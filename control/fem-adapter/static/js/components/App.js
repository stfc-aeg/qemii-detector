function App()
{
    this.mount = document.getElementById("app");
    this.current_adapter = 0;
    this.adapters = {};
    this.error_message = null;
    this.error_timeout = null;

    //Retrieve metadata for each adapter
    var meta = {};
    var promises = adapters.map(
        function(adapter, i)
        {
            return apiGET(i, "", true).then(
                function(data)
                {
                    meta[adapter] = data;
                }
            );
        }
    );

    //Then generate the page and start the update loop
    $.when.apply($, promises)
    .then(
        (function()
        {
            this.generate(meta);
            setTimeout(this.update.bind(this), this.update_delay * 1000);
        }).bind(this)
    );
}

App.prototype.freq_overlay = null;
App.prototype.query_overlay = null;
App.prototype.logging_overlay = null;
App.prototype.update_delay = 0.2;
App.prototype.dark_mode = false;

//Submit GET request then update the current adapter with new data
App.prototype.update =
    function()
    {
        var updating_adapter = this.current_adapter;
        apiGET(updating_adapter, "", false)
        .done(
            (function(data)
            {
                this.adapters[adapters[updating_adapter]].update(data);
                setTimeout(this.update.bind(this), this.update_delay * 1000);
            }).bind(this)
        )
        .fail(this.setError.bind(this));
    };


//Construct page and call components to be constructed
App.prototype.generate =
    function(meta)
    {
        //Construct navbar
        var navbar = document.createElement("nav");
        navbar.classList.add("navbar");
        navbar.classList.add("navbar-inverse");
        navbar.classList.add("navbar-fixed-top");
        navbar.innerHTML = `
<div class="container-fluid">
    <div class="navbar-header">
        <div class="navbar-brand">
            Odin Server
        </div>
    </div>
    <img class="logo" src="img/stfc_logo.png">
    <ul class="nav navbar-nav" id="adapter-links"></ul>

    <ul class="nav navbar-nav navbar-right">
        <li class="dropdown">
            <a class="dropdown-toggle" href=# data-toggle="dropdown">
                Options
                <span class="caret"></span>
            </a>
            <ul class="dropdown-menu">
                <li><a href="#" id="update-freq">Update Frequency</a></li>
                <li><a href="#" id="switch-logging">Logging</a></li>
                <li><a href="#" id="raw-query">Raw Query</a></li>
                <li><a href="#" id="toggle-dark">Toggle Dark</a></li>
            </ul>
        </li>
    </ul>
</div>`;
        this.mount.appendChild(navbar);
        document.getElementById("update-freq").addEventListener("click", this.updateFrequency.bind(this));
        document.getElementById("toggle-dark").addEventListener("click", this.toggleDark.bind(this));
        document.getElementById("switch-logging").addEventListener("click", this.switchLogging.bind(this));
        this.documentBody = document.getElementsByTagName("body")[0];
        document.getElementById("raw-query").addEventListener("click", this.rawQuery.bind(this));
        var nav_list = document.getElementById("adapter-links");

        //Create error bar
        var error_bar = document.createElement("div");
        error_bar.classList.add("error-bar");
        this.mount.appendChild(error_bar);
        this.error_message = document.createTextNode("");
        error_bar.appendChild(this.error_message);

        //Add adapter pages
        for(var key in meta)
        {
            //Create DOM node for adapter
            var container = document.createElement("div");
            container.id = "adapter-" + key;
            container.classList.add("adapter-page");
            this.mount.appendChild(container);

            var adapter_name = Component.utils.getName(meta, key);
            this.adapters[key] = new Adapter(this, container, adapter_name, meta[key]);

            //Update navbar
            var list_elem = document.createElement("li");
            nav_list.appendChild(list_elem);
            var link = document.createElement("a");
            link.href = "#";
            list_elem.appendChild(link);
            var link_text = document.createTextNode(adapter_name);
            link.appendChild(link_text);
            
            link.addEventListener("click", this.changeAdapter.bind(this, [adapters.indexOf(key)]));
        }

        document.getElementById("adapter-" + adapters[this.current_adapter]).classList.add("active");


       //Add Testing Page
       //Create DOM node for adapter
       var container = document.createElement("div");
       container.id = "testing_page";
       container.classList.add("adapter-page");
       container.innerHTML = `
<div id="test-container" class="flex-container">
    <div class ="child-column">
        <h3>Backplane Tests</h3>
        <h5>I2C component tests for the backplane on QEM.</h5>
        <div class="flex-container">
            <h5>Serial Number:</h5>
            <div class="input-group" title="Serial Number for the QEM Backplane">
               <input id="serial-number" class="form-control" placeholder="SN:01" value="SN:01" type="text">
            </div>
        </div>
        <div class="input-group" title="Start generating a report which will include all tests added to it til Stop Generating Report is pressed">
            <button id="test-report-button" class="btn btn-default" type="button">Start Generating Report</button>
        </div>
        <div class="child">
            <div class="child-header">
                <div id="test-clock-collapse" class="collapse-button">
                    <div class="collapse-table">
                        <span id="test-clock-button-symbol" class="collapse-cell glyphicon glyphicon-triangle-bottom"></span>
                    </div>
                </div>
                <h4>Clock</h4>
            </div>
            <div id="test-clock-container" class="flex-container">
                <h5>Test cases:</h5>
                <div class="input-group" title="Clock frequency for the SI570 oscillator">
                   <input id="test-clock-input" class="form-control text-right" aria-label="Test Cases" placeholder="10,50,100,20" type="text">
                </div>
                <div class="input-group-btn">
                    <button id="test-clock-button" class="btn btn-default" type="button">Run Clock Test</button>
                </div>
            </div>
        </div>
        <div class="child">
            <div class="child-header">
                <div id="test-volt-collapse" class="collapse-button">
                    <div class="collapse-table">
                        <span id="test-volt-button-symbol" class="collapse-cell glyphicon glyphicon-triangle-bottom"></span>
                    </div>
                </div>
                <h4>Current Voltage</h4>
            </div>
            <div id="test-volt-container" class="flex-container">
                <div class="checkboxes">
                    <div>
                        <input type="checkbox" id="volt-check-0" name="supply" value="VDDO">
                        <label for="volt-check-0">VDDO</label>
                        <input type="checkbox" id="volt-check-1" name="supply" value="VDD_D18">
                        <label for="volt-check-1">VDD D18</label>
                        <input type="checkbox" id="volt-check-2" name="supply" value="VDD_D25">
                        <label for="volt-check-2">VDD D25</label>
                    </div>
                    <div>
                        <input type="checkbox" id="volt-check-3" name="supply" value="VDD_P18">
                        <label for="volt-check-3">VDD P18</label>
                        <input type="checkbox" id="volt-check-4" name="supply" value="VDD_A18_PLL">
                        <label for="volt-check-4">VDD_A18_PLL</label>
                        <input type="checkbox" id="volt-check-5" name="supply" value="VDD_D18ADC">
                        <label for="volt-check-5">VDD D18ADC</label>
                    </div>
                    <div>
                        <input type="checkbox" id="volt-check-6" name="supply" value="VDD_D18_PLL">
                        <label for="volt-check-6">VDD_D18_PLL</label>
                        <input type="checkbox" id="volt-check-7" name="supply" value="VDD_RST">
                        <label for="volt-check-7">VDD RST</label>
                        <input type="checkbox" id="volt-check-8" name="supply" value="VDD_A33">
                        <label for="volt-check-8">VDD A33</label>
                    </div>
                    <div>
                        <input type="checkbox" id="volt-check-9" name="supply" value="VDD_D33">
                        <label for="volt-check-9">VDD D33</label>
                        <input type="checkbox" id="volt-check-10" name="supply" value="VCTRL_NEG">
                        <label for="volt-check-10">VCTRL NEG</label>
                        <input type="checkbox" id="volt-check-11" name="supply" value="VRESET">
                        <label for="volt-check-11">VRESET</label>
                    </div>
                    <div>
                        <input type="checkbox" id="volt-check-12" name="supply" value="VCTRL_POS">
                        <label for="volt-check-12">VCTRL POS</label>
                    </div>
                    <div>
                        <input type="checkbox" id="volt-check-all" name="supply" value="Check_All">
                        <label for="volt-check-all">Check All?</label>
                    </div>
                    <div class="input-group-btn">
                        <button id="test-volt-button" class="btn btn-default" type="button">Run Voltage Test</button>
                        <button id="test-current-button" class="btn btn-default" type="button">Run Current Test</button>
                    </div>
                </div>
            </div>
        </div>
        <div class="child">
            <div class="child-header">
                <div id="test-resist-collapse" class="collapse-button">
                    <div class="collapse-table">
                        <span id="test-resist-button-symbol" class="collapse-cell glyphicon glyphicon-triangle-bottom"></span>
                    </div>
                </div>
                <h4>Resistors</h4>
            </div>
            <div id="test-resist-container" class="flex-container">
                <div class="radios">
                    <div>
                        <input type="radio" id="resist-check-0" name="resistor" value="AUXRESET" checked>
                        <label for="resist-check-0">AUXRESET</label>
                        <input type="radio" id="resist-check-1" name="resistor" value="VCM">
                        <label for="resist-check-1">VCM</label>
                    </div>
                    <div>
                        <input type="radio" id="resist-check-2" name="resistor" value="DACEXTREF">
                        <label for="resist-check-2">DACEXTREF</label>
                        <input type="radio" id="resist-check-3" name="resistor" value="VDD_RST">
                        <label for="resist-check-3">VDD RST</label>
                    </div>
                    <div>
                        <input type="radio" id="resist-check-4" name="resistor" value="VRESET">
                        <label for="resist-check-4">VRESET</label>
                        <input type="radio" id="resist-check-5" name="resistor" value="VCTRL">
                        <label for="resist-check-5">VCTRL</label>
                    </div>
                    <div>
                        <input type="radio" id="resist-check-6" name="resistor" value="AUXSAMPLE">
                        <label for="resist-check-6">AUXSAMPLE</label>
                    </div>
                    <div>
                        <input type="checkbox" id="resist-check-graph" name="resistor_graph" value="Generate_Graph" checked>
                        <label for="resist-check-graph">Generate Graph?</label>
                    </div>
                    <div>
                        <input type="checkbox" id="resist-check-range" name="resistor_range" value="Test_Range" checked>
                        <label for="resist-check-range">Test Range?</label>
                    </div>
                    <div id="test-resist-reverse-container" class="flex-container">
                        <div>
                            <input type="checkbox" id="resist-check-reverse" name="resistor_reverse" value="Test_Reverse">
                            <label for="resist-check-reverse">Reverse Test Range?</label>
                        </div>
                    </div>
                    <div id="test-resist-cases-container" class="flex-container">
                        <h5>Test cases:</h5>
                        <div class="input-group">
                            <input id="test-resist-input-cases" class="form-control text-right" aria-label="Test Cases" placeholder="" type="text">
                        </div>
                    </div>
                    <div id="test-resist-range-container" class="flex-container">
                        <h5>Min:</h5>
                        <div class="input-group" title="Resistance Register Values">
                            <input type="number" id="test-resist-input-min" min=0 max=255 class="form-control text-right" aria-label="Minimun" placeholder="0" type="text">
                        </div>
                        <h5>Max:</h5>
                        <div class="input-group" title="Resistance Register Values">
                            <input type="number" id="test-resist-input-max" min=0 max=255 class="form-control text-right" aria-label="Maximum" placeholder="255" type="text">
                        </div>
                        <h5>Step:</h5>
                        <div class="input-group" title="Resistance Register Values">
                            <input type="number" id="test-resist-input-step" min=1 max=255 class="form-control text-right" aria-label="Step" placeholder="17" type="text">
                        </div>
                    </div>
                    <div class="input-group-btn">
                        <button id="test-resist-button-0" class="btn btn-default" type="button">Run Manual Resistor Test</button>
                        <button id="test-resist-button-1" class="btn btn-default" type="button">Run Automatic Resistor Test</button>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
`;

       this.mount.appendChild(container);
       document.getElementById("test-resist-cases-container").style.display='none';

       document.getElementById("test-report-button").addEventListener("click", this.testReport.bind(this));
       document.getElementById("test-clock-button").addEventListener("click", this.testClock.bind(this));
       document.getElementById("test-volt-button").addEventListener("click", this.testVolt.bind(this));
       document.getElementById("test-current-button").addEventListener("click", this.testCurrent.bind(this));
       document.getElementById("test-resist-button-0").addEventListener("click", this.testResist.bind(this,0));
       document.getElementById("test-resist-button-1").addEventListener("click", this.testResist.bind(this,1));
       document.getElementById("test-clock-collapse").addEventListener("click", this.toggleCollapsedClock.bind(this));
       document.getElementById("test-volt-collapse").addEventListener("click", this.toggleCollapsedVolt.bind(this));
       document.getElementById("test-resist-collapse").addEventListener("click", this.toggleCollapsedResist.bind(this));
       document.getElementById("volt-check-all").addEventListener("click", function() {
           $('#test-volt-container input[type="checkbox"]' ).prop('checked', this.checked);
       });
       document.getElementById("resist-check-range").addEventListener("click", function() {
           if(this.checked) {
               document.getElementById("test-resist-cases-container").style.display='none';
               document.getElementById("test-resist-range-container").style.display='flex';
               document.getElementById("test-resist-reverse-container").style.display='flex';
           } else {
               document.getElementById("test-resist-cases-container").style.display='flex';
               document.getElementById("test-resist-range-container").style.display='none';
               document.getElementById("test-resist-reverse-container").style.display='none';

           }
       });      

       //Update navbar
       var list_elem = document.createElement("li");
       nav_list.appendChild(list_elem);
       var link = document.createElement("a");
       link.href = "#";
       list_elem.appendChild(link);
       var link_text = document.createTextNode("Testing");
       link.appendChild(link_text);
       link.addEventListener("click", this.changePage.bind(this));


        //Add overlays
        //Change frequency
        this.freq_overlay = document.createElement("div");
        this.freq_overlay.classList.add("overlay-background");
        this.freq_overlay.classList.add("hidden");
        this.freq_overlay.innerHTML = `
<div class="overlay-freq">
    <h5>Set the frequency to update the webpage:</h5>
    <div>
        <div class="input-group">
            <input class="form-control text-right" id="frequency-value" placeholder="5" type="text">
            <span class="input-group-addon">Hz</span>
        </div>
        <div class="overlay-control-buttons">
            <button class="btn btn-success" id="frequency-set" type="button">Set</button>
            <button class="btn btn-danger" id="frequency-cancel" type="button">Cancel</button>
        </div>
    <div>
</div>
`;
        this.mount.appendChild(this.freq_overlay);
        document.getElementById("frequency-cancel").addEventListener("click", this.frequencyCancel.bind(this));
        document.getElementById("frequency-set").addEventListener("click", this.frequencySet.bind(this));

        //Raw query
        this.query_overlay = document.createElement("div");
        this.query_overlay.classList.add("overlay-background");
        this.query_overlay.classList.add("hidden");
        this.query_overlay.innerHTML = `
<div class="overlay-query">
    <h5>Raw query:</h5>
    <div class="overlay-query-padding">
        <label>Body:</label>
        <textarea class="form-control noresize" rows="5" id="query-body"></textarea>
        <label>URL:</label>
        <div class="input-group">
            <input class="form-control text-right" id="query-url" placeholder="/" type="text">
        </div>
        <label>Metadata: <input id="query-meta" type="checkbox"></label>
        <div class="overlay-control-buttons">
            <button class="btn btn-primary" id="query-put" type="button">PUT</button>
            <button class="btn btn-primary" id="query-get" type="button">GET</button>
            <button class="btn btn-danger" id="query-cancel" type="button">Cancel</button>
        </div>
    </div>
</div>
`;
        this.mount.appendChild(this.query_overlay);
        document.getElementById("query-cancel").addEventListener("click", this.queryCancel.bind(this));
        document.getElementById("query-put").addEventListener("click", this.queryPut.bind(this));
        document.getElementById("query-get").addEventListener("click", this.queryGet.bind(this));


        this.logging_overlay = document.createElement("div");
        this.logging_overlay.classList.add("overlay-background");
        this.logging_overlay.classList.add("hidden");
        this.logging_overlay.innerHTML = `
<div class="overlay-logging">
    <h5>Logging:</h5>
    <div class="overlay-logging-padding">
        <label>URL:</label>
        <div class="input-group">
            <input class="form-control text-right" id="logging-url" placeholder="localhost" type="text">
        </div>
        <label>Port:</label>
        <div class="input-group">
            <input class="form-control text-right" id="logging-port" placeholder="8086" type="text">
        </div>
        <div class="overlay-control-buttons">
            <button class="btn btn-primary" id="logging-toggle" type="button">Start</button>
            <button class="btn btn-danger" id="logging-cancel" type="button">Cancel</button>
        </div>
    </div>
</div>
`;
        this.mount.appendChild(this.logging_overlay);
        document.getElementById("logging-toggle").addEventListener("click", this.loggingToggle.bind(this));
        document.getElementById("logging-cancel").addEventListener("click", this.loggingCancel.bind(this));

        //Add footer
        var footer = document.createElement("div");
        footer.classList.add("footer");
        footer.innerHTML = `
<p>
    Odin server: <a href="www.github.com/odin-detector/odin-control">www.github.com/odin-detector/odin-control</a>
</p>
<p>
    API Version: ${api_version}
</p>`;
        this.mount.appendChild(footer);
        
        if(this.getCookie("dark") === "true")
            this.toggleDark();
    };

//Handles onClick events from the navbar
App.prototype.changeAdapter =
    function(adapter)
    {
        document.getElementById("testing_page").classList.remove("active");
        document.getElementById("adapter-" + adapters[this.current_adapter]).classList.remove("active");
        document.getElementById("adapter-" + adapters[adapter]).classList.add("active");

        this.current_adapter = adapter;
    };


App.prototype.changePage =
    function()
    {
        document.getElementById("adapter-" + adapters[this.current_adapter]).classList.remove("active");
        document.getElementById("testing_page").classList.add("active");
        this.current_adapter = adapters.indexOf("qem");
    };

App.prototype.toggleCollapsedClock =
    function()
    {
        document.getElementById("test-clock-container").classList.toggle("collapsed");
        document.getElementById("test-clock-button-symbol").classList.toggle("glyphicon-triangle-right");
        document.getElementById("test-clock-button-symbol").classList.toggle("glyphicon-triangle-bottom");
    };

App.prototype.toggleCollapsedVolt =
    function()
    {
        document.getElementById("test-volt-container").classList.toggle("collapsed");
        document.getElementById("test-volt-button-symbol").classList.toggle("glyphicon-triangle-right");
        document.getElementById("test-volt-button-symbol").classList.toggle("glyphicon-triangle-bottom");
    };

App.prototype.toggleCollapsedResist =
    function()
    {
        document.getElementById("test-resist-container").classList.toggle("collapsed");
        document.getElementById("test-resist-button-symbol").classList.toggle("glyphicon-triangle-right");
        document.getElementById("test-resist-button-symbol").classList.toggle("glyphicon-triangle-bottom");
    };

function getSerialNumber () {
    var SerialNumber = document.getElementById('serial-number').value;
    if(SerialNumber.length==0){
        SerialNumber = "SN:01";
    }
    return SerialNumber;
}

function getDate () {
    var today = new Date();
    var date = today.getDate()+'/'+(today.getMonth()+1)+'/'+today.getFullYear();
    return date;
}

function htmlHead (title) {
    return `<!DOCTYPE html>
<html>
    <head>
        <meta charset="UTF-8">
        <meta http-equiv="X-UA-Compatible" content="IE=edge">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>table, th, td {border: 1px solid black;border-collapse: collapse;padding: 5px;} td {text-align: right;}</style>
        <title>QEM ${title} Report</title>
    </head>
    <body>
        <h5>Backplane Serial Number: ${getSerialNumber()}</h5>
        <h5>Date: ${getDate()}</h5>`;

}

function chartStep(min,max,steps) {
    var baseStep = Math.ceil((max-min)/10);
    var step = steps[0];
    for(var i=0;i<steps.length;i++) {
        var newOffset = Math.abs(steps[i]-baseStep);
        var oldOffset = Math.abs(step-baseStep);
        if (newOffset<oldOffset) {
            step=steps[i];
        }
    }
    if (step<1.5*baseStep && step>(2/3)*baseStep) {
        return step;
    }
    return baseStep;
}

function chartOptions(legend,min,max,step=16) {
    var options = `
                    options: {
                        showLines: true,
                        scales: {
                            xAxes: [{
                                ticks: {
                                    min: ${min},
                                    max: ${max},
                                    stepSize: ${step},
                                }
                            }]
                        },`;
    if (!legend) {
        options += `
                        legend: {
                            display: false
                        }`;
    }
    options +=`
                    }`;
    return options;
}

function getMeasure (type,failed,testCase,resistor = "") {
     if(type==0){
         if(failed==1){
             measured = prompt("Please input the measured clock frequency",testCase);
         } else {
             measured = prompt(`Failed: ${failed} is not a number  - Please input the measured clock frequency`,testCase);
         }
     } else if(type==1) {
         if(failed==1){
             measured = prompt("Please input the measured voltage between " + resistLocation[resistor]  + " in " + resistUnits[resistor] ,testCase);;
         } else {
             measured = prompt(`Failed: ${failed} is not a number  - Please input the measured voltage between ${resistLocation[resistor]} in ${resistUnits[resistor]}`,testCase);
         }
     }
     if(measured==null){
         return;
     } else if(isNaN(measured) || measured.length==0) {
         return getMeasure(type,measured,testCase,resistor);
     } else {
         return measured;
     }
}

var report_window_html = "";
var clock_tests_html = "";
var volt_tests_html = "";
var current_tests_html = "";
var resistor_tests_html = [];
var reporting = false;
var report_graph = new Array(7);
var report_graph_data = new Array(7);
var report_graph_min = new Array(7);
var report_graph_max = new Array(7);
var report_graph_step = new Array(7);

App.prototype.testReport =
    function() { 
        if (!reporting) {
            reporting = true;
            report_graph =[[false,false],[false,false],[false,false],[false,false],[false,false],[false,false],[false,false]];
            report_graph_data=[[[],[]],[[],[]],[[],[]],[[],[]],[[],[]],[[],[]],[[],[]]];
            report_graph_min=[[255,255],[255,255],[255,255],[255,255],[255,255],[255,255],[255,255]];
            report_graph_max=[[0,0],[0,0],[0,0],[0,0],[0,0],[0,0],[0,0]];
            report_graph_step=[[[],[]],[[],[]],[[],[]],[[],[]],[[],[]],[[],[]],[[],[]]];
            $('#test-report-button').text("Stop Generating Report");
            this.report_window_html = htmlHead("Test");           
            this.clock_tests_html = "";
            this.volt_tests_html = "";
            this.current_tests_html = "";
            this.resistor_tests_html = [["",""],["",""],["",""],["",""],["",""],["",""],["",""]];
        } else {
            reporting = false;
            $('#test-report-button').text("Start Generating Report");
            if(this.clock_tests_html.length>1) {
                this.clock_tests_html += `
              </tbody>
            </table>
        </div>`;
            }
            if(this.volt_tests_html.length>1) {
                this.volt_tests_html += `
              </tbody>
            </table>
        </div>`;

            }
            if(this.current_tests_html.length>1) {
                this.current_tests_html += `
              </tbody>
            </table>
        </div>`;

            }
            this.report_window_html += this.clock_tests_html;
            this.report_window_html += this.volt_tests_html;
            this.report_window_html += this.current_tests_html;
            for(var i=0;i<7;i++){
                if (report_graph[i][0] || report_graph[i][1]){
                    this.report_window_html += `
        <script src="js/jquery-2.2.3.min.js" type="text/javascript"></script>
        <script src="js/chart.js/dist/Chart.js" type="text/javascript"></script>`;
                    break;
                }
            }
            for (var i=0;i<7;i++) {
                if (this.resistor_tests_html[i][0].length>1) {
                    this.resistor_tests_html[i][0] += `
              </tbody>
            </table>
        </div>`;
                    if (report_graph[i][0]) {
                        var report_data = report_graph_data[i][0].toString().slice(0,-1).split("/,");
                        this.resistor_tests_html[i][0] += `
        <canvas id="chart_canvus_${i}_0"></canvas>
        <script type="text/javascript">
            $(document).ready(function() {`;
                        if (report_data.length==1) {
                            this.resistor_tests_html[i][0] += `
                var resistor_data = [];`;
                            var report_data_point = report_data[0].toString().split(",");
                            for (var k=0;k<report_data_point.length;k++){
                                this.resistor_tests_html[i][0] += `
                resistor_data.push(${report_data_point[k].replace(";",",")});`;
                            }
                        } else {
                            for (var j=0;j<report_data.length;j++) {
                                this.resistor_tests_html[i][0] += `
                var resistor_data_${j} = [];`;
                                var report_data_point = report_data[j].toString().split(",");
                                for (var k=0;k<report_data_point.length;k++){
                                    this.resistor_tests_html[i][0] += `
                resistor_data_${j}.push(${report_data_point[k].replace(";", ",")});`;
                                }
                            }
                        }
                        this.resistor_tests_html[i][0] += `
                var ctx = $('#chart_canvus_${i}_0');
                var resultsChart = new Chart(ctx, {
                    type: "scatter",
                    data: {
                        datasets: [`;
                        if (report_data.length==1) {
                            this.resistor_tests_html[i][0] += `
                            {data: resistor_data}`;
                        } else {
                            for (var j=0;j<report_data.length;j++) {
                                this.resistor_tests_html[i][0] += `
                            {
                                label: "Test ${j+1}",
                                data: resistor_data_${j}
                            },`;
                            }
                        }
                        this.resistor_tests_html[i][0] += `
                        ]
                    },`
                        var min = report_graph_min[i][0];
                        var max = report_graph_max[i][0];
                        var step = chartStep(min,max,report_graph_step[i][0]);
                        if (report_data.length==1) {
                            this.resistor_tests_html[i][0] += chartOptions(false,min,max,step);
                        } else {
                            this.resistor_tests_html[i][0] += chartOptions(true,min,max,step);
                        }
                        this.resistor_tests_html[i][0] += `
                });
            });
        </script>`;
                    }

                    this.report_window_html += this.resistor_tests_html[i][0];
                }
                if (this.resistor_tests_html[i][1].length>1) {
                    this.resistor_tests_html[i][1] += `
              </tbody>
            </table>
        </div>`;
                    if (report_graph[i][1]) {
                        var report_data = report_graph_data[i][1].toString().slice(0,-1).split("/,");
                        this.resistor_tests_html[i][1] += `
        <canvas id="chart_canvus_${i}_1"></canvas>
        <script type="text/javascript">
            $(document).ready(function() {`;
                        if (report_data.length==1) {
                            this.resistor_tests_html[i][1] += `
                var resistor_data = [];`;
                            var report_data_point = report_data[0].toString().split(",");
                            for (var k=0;k<report_data_point.length;k++){
                                this.resistor_tests_html[i][1] += `
                resistor_data.push(${report_data_point[k].replace(";",",")});`;
                            }
                        } else {
                            for (var j=0;j<report_data.length;j++) {
                                this.resistor_tests_html[i][1] += `
                var resistor_data_${j} = [];`;
                                var report_data_point = report_data[j].toString().split(",");
                                for (var k=0;k<report_data_point.length;k++){
                                    this.resistor_tests_html[i][1] += `
                resistor_data_${j}.push(${report_data_point[k].replace(";", ",")});`;
                                }
                            }
                        }
                        this.resistor_tests_html[i][1] += `
                var ctx = $('#chart_canvus_${i}_1');
                var resultsChart = new Chart(ctx, {
                    type: "scatter",
                    data: {
                        datasets: [`;
                        if (report_data.length==1) {
                            this.resistor_tests_html[i][1] += `
                            {data: resistor_data}`;
                        } else {
                            for (var j=0;j<report_data.length;j++) {
                                this.resistor_tests_html[i][1] += `
                            {
                                label: "Test ${j+1}",
                                data: resistor_data_${j}
                            },`;
                            }
                        }
                        this.resistor_tests_html[i][1] += `
                        ]
                    },`;
                        var min = report_graph_min[i][1];
                        var max = report_graph_max[i][1];
                        var step = chartStep(min,max,report_graph_step[i][1]);
                        if (report_data.length==1) {
                            this.resistor_tests_html[i][1] += chartOptions(false,min,max,step);
                        } else {
                            this.resistor_tests_html[i][1] += chartOptions(true,min,max,step);
                        }
                        this.resistor_tests_html[i][1] += `
                });
            });
        </script>`;
                    }
                    this.report_window_html += this.resistor_tests_html[i][1];
                }
            }

            this.report_window_html += `
    </body>
</html>`;
            report_window = window.open();
            report_window.document.write(this.report_window_html);
            report_window.location.reload();
            report_window.print();
        }
    };

App.prototype.testClock =
    function()
    {
        $('#test-clock-button').attr('disabled', true);
        var measuredTest = [];
        var testCaseString = document.getElementById("test-clock-input").value;
        if(testCaseString.length == 0)
        {
            testCases = [10,50,100,20];
        } 
        else
        {
            testCases = testCaseString.split(',');
            for(var i=0; i<testCases.length; i++)
            {
                if(isNaN(testCases[i]) || testCases[i].length==0)
                {
                    if (confirm('Invalid test case: ' +  testCases[i] + ' is not a number. Continue?')) {
                        testCases.splice(i,1);
                        i -= 1;
                    } else {
                        $('#test-clock-button').attr('disabled', false);
                        return;
                    }
                } else if(testCases[i]<10 || testCases[i]>945){
                    if (confirm("Invalid test case: " + testCases[i] + " is not in the clocks range of 10 - 945. Continue?")) {
                        testCases.splice(i,1);
                        i -= 1;
                    } else {
                        $('#test-clock-button').attr('disabled', false);
                        return;
                    }
                } else {
                    testCases[i] = +testCases[i];
                }
            }
        }
        for(var i=0; i<testCases.length; i++)
        {
            this.put("clock",testCases[i]);
            measured = getMeasure(0,1,testCases[i]);
            if (measured == null){
                $('#test-clock-button').attr('disabled', false);
                return;
            }
            measuredTest.push(measured);
        }
        var clock_test_html = ""
        if(!reporting) {
            clock_test_html = htmlHead("Clock Test");
        }
        if(!reporting || this.clock_tests_html.length==0){
            clock_test_html += `
        <h4>Clock Test Results</h4>
        <div class='table-container'>
            <table>
              <thead>
                <tr><th>Expected</th><th>Measured</th></tr>
              </thead>
              <tbody>`;
        } else {
            clock_test_html += `
                <tr><td></td><td></td></tr>`; 
        }
        for(var i=0; i<testCases.length; i++)
        {
            clock_test_html += `
                <tr><td>${testCases[i]}</td><td>${measuredTest[i]}</td></tr>`; 
        }
        if(!reporting){ 
            clock_test_html += `
                </tbody>
            </table>
        </div>
    </body>
</html>`;
            clock_test_window = window.open();
            clock_test_window.document.write(clock_test_html);
            clock_test_window.stop();
        } else {
        this.clock_tests_html += clock_test_html;
        }
        $('#test-clock-button').attr('disabled', false);
    };


resistLookup = {7:3,10:5,11:4,12:5};

App.prototype.testVolt =
    function()
    {
        $('#test-volt-button').attr('disabled', true);
        expectedValue = [2459,2459,3415,2459,2459,2459,2459,1474,2702,2702,1638,0,0];
        expectedMaxValue ={7:2702,10:0,11:2702,12:2702};
        var promises_static = [];
        var promises_range = [[],[]];
        var testSupplies = [[],[]];
        var expectedTest = [];
        var expectedMax = [];
        var expectedMin = [];
        var measuredMin = [];
        var rangeLocation = [];
        var checkedDisabled = false;
        parentThis = this;
        for(let i=0; i<13; i++)
        {
            var CTRL_NEG_checked = document.getElementById('volt-check-10').checked;
            if(document.getElementById('volt-check-' + i).checked == true) {
                if(document.getElementById('volt-check-' + i).disabled) {
                    checkedDisabled = true;
                    continue;
                }
                if (i==7 || i>9) {
                    $(`#resist-check-${resistLookup[i]}`).attr('disabled', true);
                    if(i==10 && document.getElementById('volt-check-12').checked == true) {
                        continue;
                    }
                    testSupplies[1].push(document.getElementById('volt-check-' + i).value);
                    expectedMin.push(expectedValue[i]);
                    expectedMax.push(expectedMaxValue[i]);
                    rangeLocation.push(i);
                    if(i==12 && CTRL_NEG_checked) {
                        promises_range[0].push(new Promise ((resolve,reject) => {
                            var measuredMins = [0,0];
                            apiPUT(parentThis.current_adapter, "resistors/" + resistLookup[i] + "/register",0)
                            .done(
                                function() {
                                    setTimeout(function() {
                                        apiGET(parentThis.current_adapter, "current_voltage", false)
                                        .done(
                                            function(measuredMin) {
                                                measuredMins[0] = measuredMin["current_voltage"][i]["voltage_register"];
                                                measuredMins[1] = measuredMin["current_voltage"][10]["voltage_register"];
                                                resolve(measuredMins);
                                            }
                                        )
                                    }, 100);
                                }
                            )
                            .fail(this.setError.bind(this));
                        }));
                    } else {
                        promises_range[0].push(new Promise ((resolve,reject) => {
                            apiPUT(parentThis.current_adapter, "resistors/" + resistLookup[i] + "/register",0)
                            .done(
                                function() {
                                    setTimeout(function() {
                                        apiGET(parentThis.current_adapter, "current_voltage/" + i  + "/voltage_register", false)
                                        .done(
                                            function(measuredMin) {
                                                resolve(measuredMin);
                                            }
                                        )
                                    }, 100);
                                }
                            )
                            .fail(this.setError.bind(this));
                        }));
                    }
                } else {
                    testSupplies[0].push(document.getElementById('volt-check-' + i).value);
                    expectedTest.push(expectedValue[i]);
                    promises_static.push(apiGET(this.current_adapter, "current_voltage/" + i + "/voltage_register", false));
                }
            }
        }
        if(testSupplies[0].length == 0 && testSupplies[1].length == 0) {
             if(checkedDisabled) {
                 alert("Supplies directly linked to resistors currently being tested cannot themselves be tested")
                 $('#test-volt-button').attr('disabled', false);
                 return;
             } else {
                alert("Please select the power supplies you wish to test");
                $('#test-volt-button').attr('disabled', false);
                return;
            }
        }
        for (let i=0;i<promises_range[0].length;i++){
            promises_range[0][i].then((measuredMin) => {
                if (rangeLocation[i]==12 && CTRL_NEG_checked==true) {
                    var measuredMaxs = [0,0]
                    promises_range[1][i] = new Promise((resolve,reject) => {
                        apiPUT(parentThis.current_adapter, "resistors/" + resistLookup[rangeLocation[i]] + "/register",255)
                        .done(
                            function() {
                                setTimeout(function() {
                                    apiGET(parentThis.current_adapter, "current_voltage", false)
                                    .done(
                                        function(measuredMax) {
                                            measuredMaxs[0] = measuredMax["current_voltage"][rangeLocation[i]]["voltage_register"];
                                            measuredMaxs[1] = measuredMax["current_voltage"][10]["voltage_register"];
                                            resolve([measuredMin,measuredMaxs]);
                                        }
                                    )
                                }, 100);
                            }
                        )
                        .fail(this.setError.bind(this));
                    });
                } else {
                    promises_range[1][i] = new Promise((resolve,reject) => {
                        apiPUT(parentThis.current_adapter, "resistors/" + resistLookup[rangeLocation[i]] + "/register",255)
                        .done(
                            function() {
                                setTimeout(function() {
                                    apiGET(parentThis.current_adapter, "current_voltage/" + rangeLocation[i]  + "/voltage_register", false)
                                    .done(
                                        function(measuredMax) {
                                            resolve([measuredMin,measuredMax]);
                                        }
                                    )
                                }, 100);
                            }
                        )
                        .fail(this.setError.bind(this));
                    });
                }
            });
        }
        $.when.apply($, promises_static).then(function() {
            var volt_test_html = "";
            if(!reporting) {
                volt_test_html = htmlHead("Volt Test");
            }
            if(!reporting || parentThis.volt_tests_html.length==0) {
                volt_test_html += `
        <h4>Voltage Test Results</h4>
        <div class='table-container'>
            <table>`;
            }
            if (!reporting && expectedMax.length==0) {
                volt_test_html += `
              <thead>
                <tr><td></td><th>Expected</th><th>Measured</th></tr>
              </thead>
              <tbody>`;
                if(testSupplies[0].length==1) {
                    volt_test_html += `
                <tr><th>${testSupplies[0][0]}</th><td>${expectedTest[0]}</td><td>${arguments[0]['voltage_register'].toString()}</td></tr>`;
                } else {
                    for(var i=0; i<promises_static.length; i++)
                    {
                        volt_test_html += `
                <tr><th>${testSupplies[0][i]}</th><td>${expectedTest[i]}</td><td>${arguments[i][0]['voltage_register'].toString()}</td></tr>`;
                    }
                }
            } else {
                if (!reporting || parentThis.volt_tests_html.length==0) {
                    volt_test_html += `
              <thead>
                <tr><td></td><th>Expected Min</th><th>Measured Min</th><th>Expected Max</th><th>Measured Max</th></tr>
              </thead>
              <tbody>`;
                } else {
                    volt_test_html += `
                <tr><th></th><td></td><td></td><td></td></tr>`;
                }
                if(testSupplies[0].length==1) {
                    volt_test_html += `
                <tr><th>${testSupplies[0][0]}</th><td>${expectedTest[0]}</td><td>${arguments[0]['voltage_register'].toString()}</td><td></td><td></td></tr>`;
                } else {
                    for(var i=0; i<promises_static.length; i++){
                        volt_test_html += `
                <tr><th>${testSupplies[0][i]}</th><td>${expectedTest[i]}</td><td>${arguments[i][0]['voltage_register'].toString()}</td><td></td><td></td></tr>`;
                    }
                }
            }
            Promise.all(promises_range[0]).then((results) => {
                Promise.all(promises_range[1]).then((measured) => {
                    for(var i=0; i<promises_range[1].length; i++){
                        $(`#resist-check-${resistLookup[rangeLocation[i]]}`).attr('disabled', false);
                        if (rangeLocation[i]==12 && CTRL_NEG_checked==true) {
                            volt_test_html += `
                <tr><th>${testSupplies[1][i]}</th><td>${expectedMin[i]}</td><td>${measured[i][0][0].toString()}</td><td>${expectedMax[i]}</td><td>${measured[i][1][0].toString()}</td></tr>
                <tr><th>VCTRL_NEG</th><td>1638</td><td>${measured[i][0][1].toString()}</td><td>0</td><td>${measured[i][1][1].toString()}</td></tr>`;
                        } else {
                            volt_test_html += `
                <tr><th>${testSupplies[1][i]}</th><td>${expectedMin[i]}</td><td>${measured[i][0]['voltage_register'].toString()}</td><td>${expectedMax[i]}</td><td>${measured[i][1]['voltage_register'].toString()}</td></tr>`;
                        }
                    }
                    if(!reporting) {
                        volt_test_html += `
              </tbody>
            </table>
        </div>
    </body>
</html>`;
                        volt_test_window = window.open();
                        volt_test_window.document.write(volt_test_html);
                        volt_test_window.stop();
                    } else {
                        parentThis.volt_tests_html += volt_test_html;
                    }
                    $('#test-volt-button').attr('disabled', false);
                });
            });
        }, function() {
            this.setError.bind(this);
        });
    };


var testSupplies = [];
var expectedTest = [];
var currentMeasuredBase = [];

App.prototype.testCurrent =
    function()
    {
        $('#test-current-button').attr('disabled', true);
        expectedValue = [[20,41],[8,16],[9,18],[8,16],[82,164],[8,16],[82,164],[20,41],[20,41],[20,41],[49,98],[20,41],[82,164]];
        var promisesBase = [];
        var promisesInitialize = [];
        var testLocation = [];
        var testInitializing = [];
        testSupplies = [];
        expectedTest = [];
        parentThis = this;
        var checkedDisabled = false;
        var bothCTRL = false;

        alert(`Please remove all resistors from the PL connectors`);
        apiPUT(parentThis.current_adapter, "update_required", true)
        .done(
            function() {
                setTimeout(function() {          
                    for(var i=0; i<13; i++) {
                        if(document.getElementById('volt-check-' + i).checked == true) {
                            if(document.getElementById('volt-check-' + i).disabled) {
                                checkedDisabled = true;
                            } else if(i==7 || i>10) {
                                testInitializing.push(i);
                                promisesInitialize.push(new Promise ((resolve,reject) => {
                                    apiPUT(parentThis.current_adapter, "resistors/" + resistLookup[i] + "/register", 255)
                                    .done(
                                        function(results) {
                                            var j = testInitializing.shift();
                                            testLocation.push(j);
                                            testSupplies.push(document.getElementById('volt-check-' + j).value);
                                            expectedTest.push(expectedValue[j]);
                                            setTimeout(function() {          
                                                promisesBase.push(apiGET(parentThis.current_adapter, "current_voltage/" + j + "/current_register", false));
                                                resolve(results);
                                            }, 50);
                                        }
                                    )
                                }));
                            } else if(i==10) {
                                if(document.getElementById('volt-check-12').checked){
                                    bothCTRL = true;
                                } else {
                                    testInitializing.push(i);
                                    promisesInitialize.push(new Promise ((resolve,reject) => {
                                        apiPUT(parentThis.current_adapter, "resistors/" + resistLookup[i] + "/register",0)
                                        .done(
                                            function(results) {
                                                var j = testInitializing.shift();
                                                testLocation.push(j);
                                                testSupplies.push(document.getElementById('volt-check-' + j).value);
                                                expectedTest.push(expectedValue[j]);
                                                setTimeout(function() {          
                                                    promisesBase.push(apiGET(parentThis.current_adapter, "current_voltage/" + j + "/current_register", false));
                                                    resolve(results);
                                                }, 100);
                                            }
                                        )
                                    }));
                                }
                            } else {
                                testLocation.push(i);
                                testSupplies.push(document.getElementById('volt-check-' + i).value);
                                expectedTest.push(expectedValue[i]);
                                promisesBase.push(apiGET(parentThis.current_adapter, "current_voltage/" + i + "/current_register", false));
                            }
                        }
                    }
                    $.when.apply($, promisesInitialize).then(function() {
                        setTimeout(function() {
                            if(testSupplies.length == 0) {
                                if(checkedDisabled) {
                                    alert("Supplies directly linked to resistors currently being tested cannot themselves be tested")
                                    $('#test-current-button').attr('disabled', false);
                                    return;
                                } else {
                                    alert("Please select the power supplies you wish to test");
                                    $('#test-current-button').attr('disabled', false);
                                    return;
                                }
                            }
                            $.when.apply($, promisesBase).then(function() {
                                currentMeasuredBase = arguments;
                                getSecondMeasure(parentThis,testLocation,[],bothCTRL);
                            }, function() {
                                this.setError.bind(this);
                            });
                       }, 400);
                   });
                }, 40);
            }
        )
        .fail(this.setError.bind(this));
    };

var CTRLNegBase = ""

function getSecondMeasure(parentThis, testLocation, results, CTRLswitch) {
    neededResistor = [100,100,220,100,100,100,100,330,330,330,330,330,330];
    neededConnector = [75,42,74,41,76,33,77,34,36,35,78,40,78];

    if(testLocation.length>0) {
        alert(`Please input a ${neededResistor[testLocation[0]]}R resistor across PL${neededConnector[testLocation[0]]}`);
        apiPUT(parentThis.current_adapter, "update_required", true)
        .done(
            function() {
                setTimeout(function() {
                    apiGET(parentThis.current_adapter, "current_voltage/" + testLocation[0] + "/current_register", false)
                    .done(
                        function(measured) {
                            results.push(measured['current_register']);
                            if(CTRLswitch) {
                                CTRLNegBase = ""
                                if (testLocation[0]==12) {
                                    apiPUT(parentThis.current_adapter, "resistors/" + resistLookup[10] + "/register",0)
                                    .done(
                                        function() {
                                            testLocation.push(10);
                                            testSupplies.push(document.getElementById('volt-check-10').value);
                                            expectedTest.push(expectedValue[10]);
                                            alert("Please remove the 330R resistor from PL78")
                                            apiGET(parentThis.current_adapter, "current_voltage/10/current_register", false)
                                            .done(
                                                function(baseResult) {
                                                    CTRLNegBase = baseResult['current_register'];
                                                    testLocation.shift();
                                                    getSecondMeasure(parentThis,testLocation,results, false);
                                                }
                                            )
                                        }
                                    )
                                } else {
                                    testLocation.shift();
                                    getSecondMeasure(parentThis,testLocation,results, true);
                                }
                            } else {
                                testLocation.shift();
                                getSecondMeasure(parentThis,testLocation,results, false);
                            }
                        }
                    )
                }, 40);
            }
        )
    } else {
        var current_test_html = "";
        if(!reporting) {
            current_test_html = htmlHead("Current Test");
        }
        if(!reporting || parentThis.current_tests_html.length==0) {
            current_test_html += `
        <h4>Current Test Results</h4>
        <div class='table-container'>
            <table>
              <thead>
                <tr><td></td><th>Current</th><th>Expected</th><th>Measured</th></tr>
              </thead>
              <tbody>`;
        } else {
            current_test_html += `
                <tr><th></th><td></td><td></td><td></td></tr>`;
        }
        if(CTRLNegBase=="") {
            if(testSupplies.length==1) {
                current_test_html += `
                <tr><th>${testSupplies[0]}</th><td>10mA</td><td>${expectedTest[0][0]}</td><td>${currentMeasuredBase[0]['current_register'].toString()}</td></tr>
                <tr><td></td><td>20mA</td><td>${expectedTest[0][1]}</td><td>${results[0]}</td></tr>`;
            } else {
                for(var i=0; i<results.length; i++) {
                    current_test_html += `
                <tr><th>${testSupplies[i]}</th><td>10mA</td><td>${expectedTest[i][0]}</td><td>${currentMeasuredBase[i][0]['current_register'].toString()}</td></tr>
                <tr><td></td><td>20mA</td><td>${expectedTest[i][1]}</td><td>${results[i]}</td></tr>`;
                }
            }
        } else {
            if(testSupplies.length==2) {
                current_test_html += `
                <tr><th>${testSupplies[0]}</th><td>10mA</td><td>${expectedTest[0][0]}</td><td>${currentMeasuredBase[0]['current_register'].toString()}</td></tr>
                <tr><td></td><td>20mA</td><td>${expectedTest[0][1]}</td><td>${results[0]}</td></tr>
                <tr><th>${testSupplies[1]}</th><td>10mA</td><td>${expectedTest[1][0]}</td><td>${CTRLNegBase.toString()}</td></tr>
                <tr><td></td><td>20mA</td><td>${expectedTest[1][1]}</td><td>${results[1]}</td></tr>`;
            } else {
                for(var i=0; i<results.length-1; i++) {
                    current_test_html += `
                <tr><th>${testSupplies[i]}</th><td>10mA</td><td>${expectedTest[i][0]}</td><td>${currentMeasuredBase[i][0]['current_register'].toString()}</td></tr>
                <tr><td></td><td>20mA</td><td>${expectedTest[i][1]}</td><td>${results[i]}</td></tr>`;
                }
                current_test_html += `
                <tr><th>${testSupplies[i]}</th><td>10mA</td><td>${expectedTest[i][0]}</td><td>${CTRLNegBase.toString()}</td></tr>
                <tr><td></td><td>20mA</td><td>${expectedTest[i][1]}</td><td>${results[i]}</td></tr>`;
            }
        }
        if(!reporting) {
            current_test_html += `
              </tbody>
            </table>
        </div>
    </body>
</html>`;
            current_test_window = window.open();
            current_test_window.document.write(current_test_html);
            current_test_window.stop();
        } else {
            parentThis.current_tests_html += current_test_html;
        }
        $('#test-current-button').attr('disabled', false);
    }
}


var resistTestCases = [];
var measuredResist = [];
var expectedResist = [];
var minTest = 255;
var maxTest = 0;
var stepTest = 1;
resistName = ["AUXRESET","VCM","DACEXTREF","VDD RST","VRESET","VCTRL","AUXSAMPLE"];
lookupResistVolt = {3:7,4:11,5:[12,10]};
resistLocation = ["PL47 Pin 2 and Ground","PL46 Pin 2 and Ground","PL43 Pin 1 and Ground","PL34 Pins 1 and 2","PL40 Pins 1 and 2","PL78 Pins 1 and 2","PL45 Pin 2 and Ground"];
resistUnits = ["V","V","uA","V","V","V","V"];

App.prototype.testResist =
    function(type)
    {
        $('#test-resist-button-0').attr('disabled', true);
        $('#test-resist-button-1').attr('disabled', true);
        minTest = 255;
        maxTest = 0;
        var testCases = [];
        var gen_graph = document.getElementById("resist-check-graph").checked;
        if (document.getElementById("test-resist-cases-container").style.display != "none") {
            var testCaseString = document.getElementById("test-resist-input-cases").value;
            if(testCaseString.length == 0)
            {
                alert("Please enter test cases");
                $('#test-resist-button-0').attr('disabled', false);
                $('#test-resist-button-1').attr('disabled', false);
                return;
            }
            else
            {
                testCases = testCaseString.split(',');
                for(var i=0; i<testCases.length; i++)
                {
                    if(isNaN(testCases[i]) || testCases[i].length==0)
                    {
                        if (confirm("Invalid test case: " + testCases[i] + " is not a number. Continue?")) {
                            testCases.splice(i,1);
                            i -= 1;
                        } else {
                            $('#test-resist-button-0').attr('disabled', false);
                            $('#test-resist-button-1').attr('disabled', false);
                            return;
                        }
                    }
                    testCases[i] = +testCases[i];
                    if (testCases[i]<minTest) minTest=testCases[i];
                    if (testCases[i]>maxTest) maxTest=testCases[i];
                }
                stepTest = Math.ceil((maxTest-minTest)/10);
            }
        } else {
            var testCaseMin = document.getElementById("test-resist-input-min").value;
            var testCaseMax = document.getElementById("test-resist-input-max").value;
            var testCaseStep = document.getElementById("test-resist-input-step").value;
            if(testCaseMin.length == 0) {
                testCaseMin = 0;
            } else if(isNaN(testCaseMin)) {
                alert('Invalid Minimun: ' +  testCaseMin + ' is not a number');
                $('#test-resist-button-0').attr('disabled', false);
                $('#test-resist-button-1').attr('disabled', false);
                return;
            } else {
                testCaseMin = +testCaseMin;
                if(testCaseMin<0 || testCaseMin>255) {
                    alert('Invalid Minimun: ' + testCaseMin + ' is not in range 0 - 255');
                    $('#test-resist-button-0').attr('disabled', false);
                    $('#test-resist-button-1').attr('disabled', false);
                    return;
                }
            }
            if(testCaseMax.length == 0) {
                testCaseMax = 255;
            } else if(isNaN(testCaseMax)) {
                alert('Invalid Maximum: ' +  testCaseMax + ' is not a number');
                $('#test-resist-button-0').attr('disabled', false);
                $('#test-resist-button-1').attr('disabled', false);
                return;
            } else {
                testCaseMax = +testCaseMax;
                if(testCaseMax<testCaseMin || testCaseMax>255) {
                    alert('Invalid Maximum: ' + testCaseMax + ' is not in range ' + testCaseMin + ' - 255');
                    $('#test-resist-button-0').attr('disabled', false);
                    $('#test-resist-button-1').attr('disabled', false);
                    return;
                }
            }
            if(testCaseStep.length == 0) {
                testCaseStep = 17;
            } else if(isNaN(testCaseStep)) {
                alert('Invalid Minimun: ' +  testCaseStep + ' is not a number');
                $('#test-resist-button-0').attr('disabled', false);
                $('#test-resist-button-1').attr('disabled', false);
                return;
            } else {
                testCaseStep = +testCaseStep;
                if(testCaseStep<1) {
                    alert('Invalid Step: ' + testCaseStep + ' is not positive');
                    $('#test-resist-button-0').attr('disabled', false);
                    $('#test-resist-button-1').attr('disabled', false);
                    return;
                }
            }
            var numCases = 1 + Math.floor((testCaseMax-testCaseMin)/testCaseStep);
            if(document.getElementById('resist-check-reverse').checked == true) {
                testCases = Array.apply(null, Array(numCases)).map(function (_, i) {return (testCaseMax - testCaseStep*i);});
                minTest = testCases[testCases.length-1];
                maxTest = testCases[0];
            } else {
                testCases = Array.apply(null, Array(numCases)).map(function (_, i) {return (testCaseMin + testCaseStep*i);});
                minTest = testCases[0];
                maxTest = testCases[testCases.length-1];
            }
            for (stepTest=testCaseStep;stepTest<26;stepTest += testCaseStep) {
                if ((maxTest-minTest)<=(10*stepTest)) {break;}
            }
        }
        for(var i=0; i<7; i++)
        {
            if(document.getElementById('resist-check-' + i).checked == true) {
                if(document.getElementById('resist-check-' + i).disabled) {
                    alert("Tests may not be run on active resistors.\nPlease wait for the voltage test to finish.");
                    $('#test-resist-button-0').attr('disabled', false);
                    $('#test-resist-button-1').attr('disabled', false);
                    break;
                }
                if (i==3) {
                    $('#volt-check-7').attr('disabled', true);
                } else if (i==4) {
                    $('#volt-check-11').attr('disabled', true);
                } else if (i==5) {
                    $('#volt-check-10').attr('disabled', true);
                    $('#volt-check-12').attr('disabled', true);
                }
                resistTestCases = testCases.slice(0);
                measuredResist = [];
                expectedResist = [];
                if (type==1) {
                    if (i>2 && i<6) {
                        testingResistCalculate(i,testCases,this,gen_graph);
                    } else {
                        alert("Automatic test may only be run on VDD RST, VRESET and VCTRL");
                        $('#test-resist-button-0').attr('disabled', false);
                        $('#test-resist-button-1').attr('disabled', false);
                    }
                } else {
                    if(i==2) {
                        alert("Please supply 1V at PL43 Pin 1 to restrict the current.");
                    } else if(i==4) {
                        alert("Please ensure the jumper is on PL19 Pins 1 and 2");
                    }
                    testingResist(i,testCases,this,gen_graph);
                }
            }
        }
    };


function testingResist(resistor,testCases, parentThis, gen_graph) {
    if(testCases.length>0)
    {
        apiPUT(parentThis.current_adapter, "resistors/" + resistor + "/register",testCases[0])
        .done(
            function()
            {
                var measured = getMeasure(1,1,0,resistor);
                if (measured==null){
                    $('#test-resist-button-0').attr('disabled', false);
                    $('#test-resist-button-1').attr('disabled', false);
                    return;
                }
                measuredResist.push(parseFloat(measured).toFixed(3));
                var expected = expectResist(resistor,testCases[0]).toFixed(3);
                expectedResist.push(expected);
                testCases.shift();
                testingResist(resistor,testCases, parentThis, gen_graph);
            }
        )
    }
    else
    {
        var resist_test_html = ""
        if(!reporting) {
            resist_test_html = htmlHead("Resistor Test");
            if (gen_graph) {
                resist_test_html += `
        <script src="js/jquery-2.2.3.min.js" type="text/javascript"></script>
        <script src="js/chart.js/dist/Chart.js" type="text/javascript"></script>`;
            }
        }
        if(!reporting || parentThis.resistor_tests_html[resistor][0].length==0){
            resist_test_html += `
        <h4>${resistName[resistor]} Manual Test Results</h4>`;
            if (!reporting && gen_graph==true) {
                resist_test_html += `
            <canvas id="chart_canvus_${resistor}"></canvas>`;
            }
            resist_test_html += `
        <div class='table-container'>
            <table>
              <thead>
                <tr><th>Register</th><th>Expected</th><th>Measured</th></tr>
              </thead>
              <tbody>`;
        } else {
            resist_test_html += `
                <tr><td></td><td></td><td></td></tr>`;
        }
        for(var i=0; i<measuredResist.length; i++)
        {
            resist_test_html += `
                <tr><td>${resistTestCases[i]}</td><td>${expectedResist[i]}</td><td>${measuredResist[i]}</td></tr>`;
        }
        if(!reporting) {
            resist_test_html += `
              </tbody>
            </table>
        </div>`;
            if(gen_graph) {
                resist_test_html += `
        <script type="text/javascript">
            $(document).ready(function() {
                var resistor_data = [];`;
                for(var i=0; i<measuredResist.length; i++) {
                    resist_test_html += `
                resistor_data.push({x:${resistTestCases[i]},y:${measuredResist[i]}});`;
                }
                resist_test_html += `
                var ctx = $('#chart_canvus_${resistor}');
                var resultsChart = new Chart(ctx, {
                    type: "scatter",
                    data: {
                        datasets: [{
                            data: resistor_data
                        }]
                    },`
                resist_test_html += chartOptions(false,minTest,maxTest,stepTest);
                resist_test_html += `
                });
            });
        </script>`;
            }    
            resist_test_html += `
    </body>
</html>`;
            resist_test_window = window.open();
            resist_test_window.document.write(resist_test_html);
            resist_test_window.location.reload();
        } else {
            parentThis.resistor_tests_html[resistor][0] += resist_test_html;
            if(gen_graph) {
                report_graph[resistor][0]=true;
                var resistor_data = [];
                for(var i=0; i<measuredResist.length; i++) {
                    resistor_data.push(`{x:${resistTestCases[i]};y:${measuredResist[i]}}`);
                }
                report_graph_data[resistor][0].push(resistor_data + '/');
                report_graph_min[resistor][0] = Math.min(minTest,report_graph_min[resistor][0]);
                report_graph_max[resistor][0] = Math.max(maxTest,report_graph_max[resistor][0]);
                report_graph_step[resistor][0].push(stepTest);
            }
        }
        $('#test-resist-button-0').attr('disabled', false);
        $('#test-resist-button-1').attr('disabled', false);
        if (resistor==3) {
            $('#volt-check-7').attr('disabled', false);
        } else if (resistor==4) {
            $('#volt-check-11').attr('disabled', false);
        } else if (resistor==5) {
            $('#volt-check-10').attr('disabled', false);
            $('#volt-check-12').attr('disabled', false);
        }
    }
}

function testingResistCalculate(resistor,testCases, parentThis, gen_graph) {
    if(testCases.length>0)
    {
        apiPUT(parentThis.current_adapter, "resistors/" + resistor + "/register",testCases[0])
        .done(
            function()
            {
                var expected = expectResist(resistor,testCases[0]).toFixed(3);
                expectedResist.push(expected);
                if(resistor==5) {
                    if(expected>0) {
                        var ResistVolt = lookupResistVolt[5][0];
                    } else {
                        var ResistVolt = lookupResistVolt[5][1];
                    }
                } else {
                    var ResistVolt = lookupResistVolt[resistor];
                }
                promisesCheck = checkPromise(resistor, testCases[0], parentThis).then(function(value) {
                    testCases.shift();
                    apiGET(parentThis.current_adapter, "current_voltage/" + ResistVolt + "/voltage", false)
                    .done(
                        function(measured) {
                            measuredResist.push(measured['voltage'].toFixed(3));
                            testingResistCalculate(resistor,testCases, parentThis, gen_graph);
                        }
                    )
                });
            }
        )
    } else {
        var resist_test_html = "";
        if (!reporting) {
            resist_test_html = htmlHead("Resistor Test");
            if (gen_graph) {
                resist_test_html += `
        <script src="js/jquery-2.2.3.min.js" type="text/javascript"></script>
        <script src="js/chart.js/dist/Chart.js" type="text/javascript"></script>`;
            }
        }
        if (!reporting || parentThis.resistor_tests_html[resistor][1].length==0){
            resist_test_html += `
        <h4>${resistName[resistor]} Automatic Test Results</h4>`;
            if (!reporting && gen_graph==true) {
                resist_test_html += `
            <canvas id="chart_canvus_${resistor}"></canvas>`;
            }
            resist_test_html += `
        <div class='table-container'>
            <table>
              <thead>
                <tr><th>Register</th><th>Expected</th><th>Calculated</th></tr>
              </thead>
              <tbody>`;
        } else {
            resist_test_html += `
                <tr><td></td><td></td><td></td></tr>`;
        }
        for(var i=0; i<measuredResist.length; i++)
        {
            resist_test_html += `
                <tr><td>${resistTestCases[i]}</td><td>${expectedResist[i]}</td><td>${measuredResist[i]}</td></tr>`;
        }
        if (!reporting) {
            resist_test_html += `
              </tbody>
            </table>
        </div>`;
            if(gen_graph) {
                resist_test_html += `
        <script type="text/javascript">
            $(document).ready(function() {
                var resistor_data = [];`;
                for(var i=0; i<measuredResist.length; i++) {
                    resist_test_html += `
                resistor_data.push({x:${resistTestCases[i]},y:${measuredResist[i]}});`;
                }
                resist_test_html += `
                var ctx = $('#chart_canvus_${resistor}');
                var resultsChart = new Chart(ctx, {
                    type: "scatter",
                    data: {
                        datasets: [{
                            data: resistor_data
                        }]
                    },`;
                resist_test_html += chartOptions(false,minTest,maxTest,stepTest);
                resist_test_html += `
                });
            });
        </script>`;
            }    
            resist_test_html += `
    </body>
</html>`;
            resist_test_window = window.open();
            resist_test_window.document.write(resist_test_html);
            resist_test_window.location.reload();
        } else {
            parentThis.resistor_tests_html[resistor][1] += resist_test_html;
            if(gen_graph) {
                report_graph[resistor][1]=true;
                var resistor_data = [];
                for(var i=0; i<measuredResist.length; i++) {
                    resistor_data.push(`{x:${resistTestCases[i]};y:${measuredResist[i]}}`);
                }
                report_graph_data[resistor][1].push(resistor_data + "/");
                report_graph_min[resistor][1] = Math.min(minTest,report_graph_min[resistor][1]);
                report_graph_max[resistor][1] = Math.max(maxTest,report_graph_max[resistor][1]);
                report_graph_step[resistor][1].push(stepTest);
            }
        }
        $('#test-resist-button-0').attr('disabled', false);
        $('#test-resist-button-1').attr('disabled', false);
        if (resistor==3) {
            $('#volt-check-7').attr('disabled', false);
        } else if (resistor==4) {
            $('#volt-check-11').attr('disabled', false);
        } else if (resistor==5) {
            $('#volt-check-10').attr('disabled', false);
            $('#volt-check-12').attr('disabled', false);
        }

    }
}

function expectResist(resistor,test) {
    if(resistor==4) { 
          return (0.0001 * (49900 * (390 * test)) / (49900 + (390 * test)));
    } else if(resistor==3) {   
          return(0.0001 * (17800 + (18200 * (390 * test)) / (18200 + (390 * test))));
    } else if(resistor==5) {
        return  -3.775 + (1.225/22600 + .35*.000001) * (390 * test + 32400);
    } else if(resistor==2) {
        return (400.0 * (test * 390/(test * 390 + 294000)));
    } else {
        return (3.3 * (390 * test) / (390 * test + 32000));
    }
}


function checkPromise(resistor, value, parentThis) {
    return new Promise((resolve, reject) => {
        apiPUT(parentThis.current_adapter, "reset", true)
        .done(
            function(results) {
                setTimeout(function() {
                    apiGET(parentThis.current_adapter, "resistors/" + resistor + "/register", false)
                    .done(
                        function(check) {
                            if(check['register']!=value) {
                                promiseCheck = checkPromise(resistor, value, parentThis).then(function(result) {
                                    resolve(result);
                                });
                            } else {
                                resolve("Changed");
                            }
                        }   
                    )
                }, 40);
            }
        )
    });
}


App.prototype.setError =
    function(data)
    {
        if(data.hasOwnProperty("json"))
        {
            var json = data.responseJSON;
            if(json.hasOwnProperty("error"))
                this.showError(json.error);
        }
        else
        {
            this.showError(data.responseText);
        }
    }

App.prototype.showError =
    function(msg)
    {
        if(this.error_timeout !== null) clearTimeout(this.error_timeout);
        this.error_message.nodeValue = `Error: ${msg}`;
        this.error_timeout = setTimeout(this.clearError.bind(this), 5000);
    }

App.prototype.clearError =
    function()
    {
        this.error_message.nodeValue = "";
    };

App.prototype.put =
    function(path, val)
    {
        apiPUT(this.current_adapter, path, val)
        .fail(this.setError.bind(this));
        return;
    };

App.prototype.updateFrequency =
    function()
    {
        document.getElementById("frequency-value").placeholder = (Math.round(100 / this.update_delay) / 100).toString();
        this.freq_overlay.classList.remove("hidden");
    };

App.prototype.frequencyCancel =
    function()
    {
        this.freq_overlay.classList.add("hidden");
    };

App.prototype.frequencySet =
    function()
    {
        var val = document.getElementById("frequency-value").value;
        var new_delay = 1 / parseFloat(val);

        if(isNaN(new_delay) || !isFinite(new_delay))
            this.showError("Update frequency must be a valid number");
        else
            this.update_delay = new_delay;

        document.getElementById("frequency-value").value = "";
        this.freq_overlay.classList.add("hidden");        
    };

App.prototype.toggleDark =
    function()
    {
        this.dark_mode = !this.dark_mode;
        this.setCookie("dark", this.dark_mode.toString());

        this.mount.classList.toggle("dark");
        this.documentBody.classList.toggle("background-dark");
    };

App.prototype.rawQuery =
    function()
    {
        this.query_overlay.classList.remove("hidden");
    };

App.prototype.queryCancel =
    function()
    {
        this.query_overlay.classList.add("hidden");
    };

App.prototype.queryPut =
    function()
    {
        this.put(document.getElementById("query-url").value, JSON.parse(document.getElementById("query-body").value));
    };

App.prototype.queryGet =
    function()
    {
        apiGET(this.current_adapter, document.getElementById("query-url").value, document.getElementById("query-meta").checked)
        .done(
            function(data)
            {
                document.getElementById("query-body").value = JSON.stringify(data);
            }
        )
        .fail(this.setError.bind(this));
    };

App.prototype.switchLogging =
    function()
    {
        this.logging_overlay.classList.remove("hidden");
    };

App.prototype.loggingCancel =
    function()
    {
        this.logging_overlay.classList.add("hidden");
    };

App.prototype.loggingToggle =
    function()
    {
        this.logging_overlay.classList.add("hidden");
    };


App.prototype.getCookie =
    function(key)
    {
        var raw = document.cookie.split(';');
        for(var value of raw)
        {
            if(value.indexOf(key) == 0)
                return decodeURIComponent(value.substring(key.length + 1));
        }
    };

App.prototype.setCookie =
    function(key, value)
    {
        var date = new Date();
        date.setTime(date.getTime() + 30 * (24 * 60 * 60 * 1000));
        var expires = `expires=${date.toUTCString()}`;

        var raw = document.cookie.split(';');
        raw = raw.filter((itm) => itm.indexOf("path") !== 0
                                && itm.indexOf("expires") !== 0
                                && itm.length > 0);
        var cookieString = `${key}=${encodeURIComponent(value)}`;
        var found = false;
        for(var i = 0; i < raw.length; i++)
            if(raw[i].indexOf(key) === 0)
            {
                raw[i] = cookieString;
                found = true;
            }
        if(!found)
            raw.push(cookieString);
        var s = `${raw.join(';')};${expires};path=/`;
        document.cookie = `${raw.join(';')};${expires};path=/`;
    };

//Create the App() instance
function initApp()
{
    var app = new App();
}
