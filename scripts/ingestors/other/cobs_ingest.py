"""Ingest the COBS data file

  Run from RUN_20_AFTER.sh
"""
from __future__ import print_function
import datetime
import os
import sys

import pandas as pd
import psycopg2
import pytz
from pyiem.observation import Observation
from pint import UnitRegistry

UREG = UnitRegistry()
QUANTITY = UREG.Quantity
SID = 'OT0012'
DIRPATH = "/mnt/mesonet/home/mesonet/ot/ot0005/incoming/Pederson"

HOURLYCONV = {'Batt_Volt': 'battery',
              'PTemp_C': None,  # Panel Temperature ?
              'Rain_in_Tot': 'phour',
              'SlrW_Avg': 'srad',
              'SlrMJ_Tot': None,
              'AirTF_Avg': 'tmpf',
              'RH': 'relh',
              'WS_mph_Avg': 'sknt',
              'WS_mph_Max': 'gust',
              'WindDir': 'drct',
              'WS_mph_S_WVT': None,
              'WindDir_D1_WVT': None,
              'T107_F_Avg': 'c1tmpf'}  # 4 inch soil temp

DAILYCONV = {'Batt_Volt_Min': None,
             'PTemp_C_Max': None,
             'PTemp_C_Min': None,
             'Rain_in_Tot': 'pday',
             'SlrW_Avg': None,
             'SlrW_Max': None,
             'SlrW_TMx': None,
             'SlrMJ_Tot': 'srad_mj',
             'AirTF_Max': 'max_tmpf',
             'AirTF_TMx': None,
             'AirTF_Min': 'min_tmpf',
             'AirTF_TMn': None,
             'AirTF_Avg': None,
             'RH_Max': 'max_rh',
             'RH_TMx': None,
             'RH_Min': 'min_rh',
             'RH_TMn': None,
             'WS_mph_Max': 'gust',
             'WS_mph_TMx': None,
             'WS_mph_S_WVT': None,
             'WindDir_D1_WVT': None,
             'T107_F_Max': None,
             'T107_F_TMx': None,
             'T107_F_Min': None,
             'T107_F_TMn': None,
             'T107_F_Avg': None}


def sum_hourly(hdf, date, col):
    """Figure out the sum based on the hourly data"""
    # 6z is good enough, no rad at night!
    sts = datetime.datetime(date.year, date.month, date.day, 6)
    sts = sts.replace(tzinfo=pytz.utc)
    ets = sts + datetime.timedelta(hours=24)
    df2 = hdf[(hdf['valid'] > sts) & (hdf['valid'] < ets)]
    if len(df2.index) == 0:
        print("No data found!?")
        return None
    return df2[col].sum()


def clean(key, value):
    """"Clean the values"""
    if key.startswith('WS'):
        return QUANTITY(value, UREG.mph).to(UREG.knots).m
    if key.startswith('RH') and value > 100:
        return 100.
    if pd.isnull(value):
        return None
    return value


def database(lastob, ddf, hdf, force_currentlog):
    """Do the tricky database work"""
    # This should be okay as we are always going to CST
    maxts = hdf['TIMESTAMP'].max().replace(
        tzinfo=pytz.timezone("America/Chicago"))
    if lastob is not None and maxts <= lastob:
        # print("maxts: %s lastob: %s" % (maxts, lastob))
        return
    iemdb = psycopg2.connect(database='iem', host='iemdb')
    icursor = iemdb.cursor()
    if lastob is None:
        df2 = hdf
    else:
        df2 = hdf[hdf['valid'] > lastob]
    for _, row in df2.iterrows():
        localts = row['valid'].tz_convert(pytz.timezone("America/Chicago"))
        # Find, if it exists, the summary table entry here
        daily = ddf[ddf['date'] == localts.date()]
        ob = Observation(SID, 'OT', localts)
        if len(daily.index) == 1:
            for key, value in DAILYCONV.items():
                if value is None:
                    continue
                # print("D: %s -> %s" % (key, value))
                ob.data[value] = clean(key, daily.iloc[0][key])
        # print("date: %s srad_mj: %s" % (localts.date(), ob.data['srad_mj']))
        if ob.data['srad_mj'] is None:
            ob.data['srad_mj'] = sum_hourly(hdf, localts.date(), 'SlrMJ_Tot')
        if ob.data['pday'] is None:
            ob.data['pday'] = sum_hourly(hdf, localts.date(), 'Rain_in_Tot')
            # print("  --> srad_mj: %s" % (ob.data['srad_mj'], ))
        for key, value in HOURLYCONV.items():
            if value is None:
                continue
            # print("H: %s -> %s" % (key, value))
            ob.data[value] = clean(key, row[key])
        ob.save(icursor, force_current_log=force_currentlog,
                skip_current=force_currentlog)
    icursor.close()
    iemdb.commit()


def get_last():
    """Get the last timestamp"""
    pgconn = psycopg2.connect(database='iem', host='iemdb', user='nobody')
    cursor = pgconn.cursor()
    cursor.execute("""SELECT valid at time zone 'UTC'
    from current c JOIN stations t
    ON (c.iemid = t.iemid) where t.id = %s
    """, (SID,))
    return cursor.fetchone()[0].replace(tzinfo=pytz.utc)


def campbell2df(year):
    """"Process the file for any timestamps after the lastob"""
    dailyfn = "%s/%s/Daily.dat" % (DIRPATH, year)
    hourlyfn = "%s/%s/Hourly.dat" % (DIRPATH, year)
    if not os.path.isfile(dailyfn):
        print("cobs_ingest.py missing %s" % (dailyfn,))
        return
    if not os.path.isfile(hourlyfn):
        print("cobs_ingest.py missing %s" % (hourlyfn,))
        return

    ddf = pd.read_csv(dailyfn, header=0, na_values=["7999", "NAN"],
                      skiprows=[0, 2, 3], quotechar='"', warn_bad_lines=True)
    ddf['TIMESTAMP'] = pd.to_datetime(ddf['TIMESTAMP'])
    # Timestamps should be moved back one day
    ddf['date'] = (ddf['TIMESTAMP'] - datetime.timedelta(hours=12)).dt.date
    hdf = pd.read_csv(hourlyfn, header=0, na_values=["7999", "NAN"],
                      skiprows=[0, 2, 3], quotechar='"', warn_bad_lines=True)
    hdf['TIMESTAMP'] = pd.to_datetime(hdf['TIMESTAMP'])
    hdf['SlrMJ_Tot'] = pd.to_numeric(hdf['SlrMJ_Tot'], errors='coerse')
    # Move all timestamps to UTC +6
    hdf['valid'] = (hdf['TIMESTAMP'] +
                    datetime.timedelta(hours=6)).dt.tz_localize('UTC')
    return ddf, hdf


def main(argv):
    """Go for it!"""
    if len(argv) > 1:
        print("Running special request")
        for year in range(2017, 2018):
            ddf, hdf = campbell2df(year)
            database(None, ddf, hdf, True)
    else:
        lastob = get_last()
        now = datetime.datetime.now()
        ddf, hdf = campbell2df(now.year)
        database(lastob, ddf, hdf, False)


if __name__ == '__main__':
    main(sys.argv)
