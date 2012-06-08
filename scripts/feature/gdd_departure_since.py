import iemdb
COOP = iemdb.connect('coop', bypass=True)
ccursor = COOP.cursor()

climate = [0]*366
obs = [0]*366
# Load Climate
ccursor.execute("""SELECT extract(doy from valid) as doy, gdd50 from
  climate WHERE station = 'IA0200'""")
for row in ccursor:
    climate[ int(row[0]) -1 ] = float(row[1])
    
# Load Obs
ccursor.execute("""
SELECT extract(doy from day) as doy, gdd50(high,low) from
  alldata_ia WHERE station = 'IA0200' and year = 2012""")
for row in ccursor:
    obs[ int(row[0]) -1 ] = float(row[1])

import mx.DateTime
jday = int(mx.DateTime.now().strftime("%j")) - 1
x = []
y = []
xticks = []
xticklabels = []
for i in range(0,jday+1):
    climate_total = sum(climate[jday-i:jday])
    obs_total = sum(obs[jday-i:jday])
    x.append(i)
    y.append(obs_total - climate_total)

    ts = mx.DateTime.now() - mx.DateTime.RelativeDateTime(days=i)
    if ts.day == 1:
        xticks.append( i )
        xticklabels.append( ts.strftime("%-d %b"))

import numpy
import matplotlib.pyplot as plt
fig, ax = plt.subplots(1,1)
ax2 = ax.twinx() 
ax2.set_ylabel("GDD Departure [Climatology of 15 May days]")
def Tc(Tf):
    return Tf / 11.6

def update_ax2(ax1):
   y1, y2 = ax1.get_ylim()
   ax2.set_ylim(Tc(y1), Tc(y2))
   ax2.figure.canvas.draw()

# automatically update ylim of ax2 when ylim of ax1 changes.
ax.callbacks.connect("ylim_changed", update_ax2)

ax.bar(numpy.array(x)-0.5,y, fc='r', ec='r')
ax.set_xticks(xticks)
ax.set_xlim(-0.5,max(x)+0.5)
ax.set_xticklabels( xticklabels )
ax.set_xlabel("Period from 14 May back to date")
ax.set_ylabel("Growing Degree Days Departure (base=50)")
ax.set_title("2012 Ames Growing Degree Day Departure (base=50)\nfrom climatology over periods prior to today")
ax.grid(True)

fig.savefig('test.ps')
import iemplot
iemplot.makefeature('test')