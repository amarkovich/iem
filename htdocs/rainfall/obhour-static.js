Ext.onReady(function(){

Ext.namespace('iemdata');

iemdata.networks = [
 ['IA_ASOS','Iowa ASOS'],
 ['AWOS','Iowa AWOS'],
 ['IL_ASOS','Illinois ASOS/AWOS'],
 ['WI_ASOS','Wisconsin ASOS/AWOS'],
 ['AR_ASOS','Arkansas ASOS']
];

var network_selector = new Ext.form.ComboBox({
             hiddenName:'network',
             store: new Ext.data.SimpleStore({
                      fields: ['abbr', 'name'],
                      data : iemdata.networks
             }),
             valueField:'abbr',
             displayField:'name',
             hideLabel: true,
             typeAhead: true,
             mode: 'local',
             triggerAction: 'all',
             emptyText:'Select a Network...',
             selectOnFocus:true,
             lazyRender: true,
             value:"IA_ASOS",
             width:190
});


var dateselector = new Ext.form.DateField({
    id: "df",
    hideLabel: true,
    minValue: new Date('2008/01/01'),
    maxValue: new Date(),
    value: new Date()
});

var timeselector = new Ext.form.TimeField({
    hideLabel: true,
    increment:60,
    value: new Date(),
    format:'h A',
    id: "tm"
});

var realtime = new Ext.form.Checkbox({
  id:"realtime",
  boxLabel:"Real Time Mode",
  hideLabel: true
});

var task = {
    run: function(){
      if(! realtime.checked) return;
      var localDate = new Date();
      dateselector.setValue( localDate );
      timeselector.setValue( localDate );
      var gmtDate = localDate.add(Date.SECOND, 0 - localDate.format('Z'));
      var sff = Ext.getCmp('selectform').getForm();
      var network = sff.findField('network').getValue();
      Ext.getCmp('precipgrid').setTitle("Precip Accumulation valid at "+ localDate.format('d M Y h A') ).getStore().load({
            params:'network='+network+'&ts='+gmtDate.format('YmdHi')
      });
      Ext.getCmp('statusField').setText("Grid Loaded at "+ new Date() );
      updateHeaders( localDate );

    },
    interval: 3600000 
}
Ext.TaskMgr.start(task);


var selectform = new Ext.form.FormPanel({
     frame: true,
     id: 'selectform',
     title: 'Data Chooser',
     labelWidth:0,
     buttons: [{
         text:'Load Data',
         handler: function() {
           var sff = Ext.getCmp('selectform').getForm();
           var network = sff.findField('network').getValue();
           var localDate = sff.findField('df').getValue();
           var tm = sff.findField('tm').getValue();
           var d = new Date.parseDate(tm, 'h A');
           localDate = localDate.add(Date.HOUR, d.format('H') );
           var gmtDate = localDate.add(Date.SECOND, 0 - localDate.format('Z'));
          Ext.getCmp('precipgrid').setTitle("Precip Accumulation valid at "+ localDate.format('d M Y h A') ).getStore().load({
            params:'network='+network+'&ts='+gmtDate.format('YmdHi')
          });
          Ext.getCmp('statusField').setText("Grid Loaded at "+ new Date() );
          updateHeaders( localDate );
          } // End of handler
     }],
     items: [network_selector, dateselector, timeselector, realtime]
});



var pstore = new Ext.data.Store({
      root:'precip',
      autoLoad:false,
      proxy: new Ext.data.HttpProxy({
            url: 'obhour-json.php',
            method: 'GET'
     }),
     reader:  new Ext.data.JsonReader({
        root: 'precip',
            id: 'id'
         }, [
         {name: 'id'},
         {name: 'name'},
         {name: 'pmidnight'},
         {name: 'p1'},
         {name: 'p3'},
         {name: 'p6'},
         {name: 'p12'},
         {name: 'p24'},
         {name: 'p48'},
         {name: 'p72'},
         {name: 'p96'}
     ])
});

function updateHeaders(ts) {
  var cm = gpanel.getColumnModel();
  var col;
  var ts0;
  for (i=2; i < cm.getColumnCount(); i++)
  {
    col = cm.getColumnById( cm.getColumnId(i) );
    ts0 = ts.add(Date.SECOND, 0 - (col.toffset * 3600));
    if (col.toffset == 0){ 
      ts0 = ts.add(Date.HOUR, 0 - (ts.format('H'))); 
      cm.setColumnHeader(i, "Midnight<br />"+ ts0.format('m/d hA')+"<br />"+ ts.format('m/d hA'));
    } else {
      cm.setColumnHeader(i, col.toffset +" Hour<br />"+ ts0.format('m/d hA')+"<br />"+ ts.format('m/d hA'));
    }
  }
};


var gpanel =  new Ext.grid.GridPanel({
        id:'precipgrid',
        isLoaded:false,
        store: pstore,
        region:'center',
        tbar:[new Ext.StatusBar({
            defaultText: 'Please load data from the side',
            id: 'statusField'
        })
        ],
        loadMask: {msg:'Loading Data...'},
        viewConfig:{forceFit:false},
        cm: new Ext.grid.ColumnModel([
            {header: "ID",  width: 40, sortable: true, dataIndex: 'id'},
            {header: "Name", id: "sitename", width: 150, sortable: true, dataIndex: 'name'},
            {header: "Midnight", toffset: 0, width: 80, sortable: true, dataIndex: 'pmidnight'},
            {header: "1 Hour", toffset: 1, width: 80, sortable: true, dataIndex: 'p1'},
            {header: "3 Hour", toffset: 3, width: 80, sortable: true, dataIndex: 'p3'},
            {header: "6 Hour", toffset: 6, width: 80, sortable: true, dataIndex: 'p6'},
            {header: "12 Hour", toffset: 12, width: 80, sortable: true, dataIndex: 'p12'},
            {header: "24 Hour", toffset: 24, width: 80, sortable: true, dataIndex: 'p24'},
            {header: "48 Hour", toffset: 48, width: 80, sortable: true, dataIndex: 'p48'},
            {header: "72 Hour", toffset: 72, width: 80, sortable: true, dataIndex: 'p72'},
            {header: "96 Hour", toffset: 96, width: 80, sortable: true, dataIndex: 'p96'}
        ]),
        stripeRows: true,
        title:'Accumulated Precipitation by Interval',
        autoScroll:true
    });

var tp = new Ext.Panel({
  contentEl:'sidebarinfo'
});


var viewport = new Ext.Viewport({
    layout:'border',
    items:[
         new Ext.BoxComponent({ // raw
             region:'north',
             el: 'header',
             height:60
         }),
         new Ext.BoxComponent({ // raw
             region:'south',
             el: 'footer',
             height:32
         }),
          { 
             region:'west',
             width:210,
             collapsible:true,
             title: 'Settings',
             layoutConfig:{
                animate:true
             },
             items:[selectform,tp]
         },
         gpanel
         ]
});


// End of static.js
});
