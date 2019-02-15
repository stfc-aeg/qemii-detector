function App()
{
    this.mount = document.getElementById("app");
    this.error_message = null;
    this.error_timeout = null;
    this.current_adapter = 0

//Retrieve metadata for each adapter
var meta = {};
var promises = adapters.map(
    function(adapter, i) {
        return apiGET(i, "", true).then(
            function(data) {
                meta[adapter] = data;
                this.current_adapter = i
            }
        );
    }
);

//Then generate the page and start the update loop
$.when.apply($, promises).then(
    (function() {
        this.generate(meta["interface"]);
        console.log(meta["interface"]);
        if (meta["interface"]["sensors_enabled"]["value"] == "True") {
            this.updateLoop_bp();
        }
        if (meta["interface"]["non_volatile"]["value"] == "True") {
            this.setVolatile();
            //this.setVolatileTrue();
        }
    }).bind(this)
);
}

App.prototype.freq_overlay = null;
App.prototype.update_delay = 0.5;
App.prototype.dark_mode = false;
App.prototype.in_calibration_mode = true 
App.prototype.image_interval;
App.prototype.image_loop_interval;
App.prototype.coarse_interval;
App.prototype.fine_interval;
App.prototype.plot_fine_interval;
App.prototype.plot_coarse_interval;
App.prototype.file_written_interval;
App.prototype.upload_vector_interval;



//Construct page and call components to be constructed
App.prototype.generate =
    function(data) {
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
                            <li><a href="#" id="toggle-dark">Toggle Dark</a></li>
                        </ul>
                    </li>
                </ul>
            </div>`;

            
        this.mount.appendChild(navbar);
        document.getElementById("update-freq").addEventListener("click", this.updateFrequency.bind(this));
        document.getElementById("toggle-dark").addEventListener("click", this.toggleDark.bind(this));
        this.documentBody = document.getElementsByTagName("body")[0];
        var nav_list = document.getElementById("adapter-links");

        //Create error bar
        var error_bar = document.createElement("div");
        error_bar.classList.add("error-bar");
        this.mount.appendChild(error_bar);
        this.error_message = document.createTextNode("");
        error_bar.appendChild(this.error_message);

        //Add Configuration Page
        //Create DOM node for adapter
       var container = document.createElement("div");
       container.id = "configuration-page";
       container.classList.add("adapter-page");
       container.innerHTML = `
        <div id="configure-container" class="flex-container">
            <div class="parent-column">
                <h4>Configuration</h4>
                    <p class="desc">Configuration options for the ASIC and Backplane</p>
                <div class="vertical">
                    <div>
                        <h5>Clock:</h5>
                        <div class="variable-padding">
                            <div class="padder"></div>
                        </div>
                        <div>
                            <div class="input-group" title="Clock frequency for the SI570 oscillator">
                                <input class="form-control text-right" id="clock-input" aria-label="Value" placeholder=` + Number(data["clock"]["value"]).toFixed(1).toString() + ` type="text">
                                <span class="input-group-addon">MHz</span>
                                <div class="input-group-btn">
                                    <button class="btn btn-default" id="clock-button" type="button">Set</button>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div>
                        <h5>Refresh Backplane:</h5>
                        <div class="variable-padding">
                            <div class="padder"></div>
                        </div>
                        <div>
                            <button id="bp-refresh-button" type="button" class="btn btn-default">Update</button>
                        </div>
                    </div>
                    <div>
                        <h5>Backplane Updating:</h5>
                        <div class="variable-padding">
                            <div class="padder"></div>
                        </div>
                        <div>
                            <button id="bp-update-button" type="button" class="btn btn-toggle btn-danger">Disabled</button>
                        </div>
                    </div>
                    <div>
                        <h5>Reload Backplane:</h5>
                        <div class="variable-padding">
                        <div class="padder"></div>
                    </div>
                    <div>
                        <button id="bp-reload-button" type="button" class="btn btn-default">Reload</button>
                    </div>
                </div>
            </div>
        </div>

    <div class ="child-column">
        <div class="child">
            <div id="ASIC-container" class="flex-container">
                <div id="top-flex" class="flex-item">
                    <div class="child-header">
                        <h4 class="non-drop-header">Mode</h4>
                    </div>
                    <div class='table-container-left'>
            
                        <div id="toggle-container">
                            <div class="inner-toggle-container">
                                <div class="toggle">
                                    <p>Image Capture Mode</p>
                                </div>
                                <div class="toggle">
                                    <p>Calibration Mode</p>
                                </div>
                            </div>

                            <div class="inner-toggle-container" id="inner-toggle-container">
                                <div class="toggle">
                                    <p>Image Capture Mode</p>
                                </div>
                                <div class="toggle">
                                    <p>Calibration Mode</p>
                                </div>
                            </div>
                        </div>

                    </div>

                </div>

                <div id="top-flex" class="flex-item">
                    <div class="child-header">
                        <h4>Configuration</h4>
                    </div>
                    <div class="table-container">
                       
                        <div class="dropdown-file">
                            <button id="toggle-btn" class="btn btn-primary dropdown-toggle" type="button" data-toggle="dropdown" aria-expanded="false">Configuration Vector File
                            <span class="caret"></span></button>
                            <ul class="dropdown-menu" id="file_list">` +
                            //+ this.generateImageVectorFiles(data["image_vector_files"]["value"]) + this.generateADCVectorFiles(data["adc_vector_files"]["value"]) + 
                            `</ul>
                        </div>
                        <span id="current-txt-file"></span>
                    </div>
                </div>
            </div>
        </div>


        <div class="child">
            <div class="child-header">
                <div id="BIAS-collapse" class="collapse-button">
                    <div class="collapse-table">
                        <span id="BIAS-button-symbol" class="collapse-cell    glyphicon glyphicon-triangle-bottom"></span>
                    </div>
                </div>
                <h4>BIAS Settings</h4>
            </div>
            <div id="BIAS-container" class="flex-container">
            <div class="flex-item">
                <div class="table-container-left">
                    <table>
                        <thead>
                            <tr>
                                <th></th>
                                <th>Value</th>
                                <th></th>
                                <th>Value</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <th class="text-right">iBiasCol</th>
                                <td>
                                    <div class="input-group">
                                        <input class="form-control text-right bias" id="DAC-0-input" aria-label="Value" placeholder="010100" type="text" maxlength='6'>
                                        <span id='dac-0-addon' class="input-group-addon">20</span>
                                    </div>
                                </td>
                                <th class="text-right">iBiasSF0</th>
                                <td>
                                    <div class="input-group">
                                        <input class="form-control text-right bias" id="DAC-1-input" aria-label="Value" placeholder="001100" type="text" maxlength='6'>
                                        <span id='dac-1-addon' class="input-group-addon">12</span>
                                    </div>
                                </td>
                            </tr>
                            <tr>
                                <th class="text-right">vBiasPGA</th>
                                <td>
                                    <div class="input-group">
                                        <input class="form-control text-right bias" id="DAC-2-input" aria-label="Value" placeholder="101101" type="text" maxlength='6'>
                                        <span id='dac-2-addon' class="input-group-addon">45</span>
                                    </div>
                                </td>
                                <th class="text-right">iBiasPGA</th>
                                <td>
                                    <div class="input-group">
                                        <input class="form-control text-right bias" id="DAC-3-input" aria-label="Value" placeholder="001100" type="text" maxlength='6'>
                                        <span id='dac-3-addon' class="input-group-addon">12</span>
                                    </div>
                                </td>
                            </tr>
                            <tr>
                                <th class="text-right">iBiasSF1</th>
                                <td>
                                    <div class="input-group">
                                        <input class="form-control text-right bias" id="DAC-4-input"  aria-label="Value" placeholder="010000" type="text" maxlength='6'>
                                        <span id='dac-4-addon' class="input-group-addon">16</span>
                                    </div>
                                </td>
                                <th class="text-right">iBiasOutSF</th>
                                <td>
                                    <div class="input-group">
                                        <input class="form-control text-right bias" id="DAC-5-input" aria-label="Value" placeholder="001010" type="text" maxlength='6'>
                                        <span id='dac-5-addon' class="input-group-addon">10</span>
                                    </div>
                                </td>
                            </tr>
                            <tr>
                                <th class="text-right">iBiasLoad</th>
                                <td>
                                    <div class="input-group">
                                        <input class="form-control text-right bias" id="DAC-6-input" aria-label="Value" placeholder="010100" type="text" maxlength='6'>
                                        <span id='dac-6-addon' class="input-group-addon">20</span>
                                    </div>
                                </td>
                                <th class="text-right">iBiasADCbuffer</th>
                                <td>
                                    <div class="input-group">
                                        <input class="form-control text-right bias" id="DAC-7-input" aria-label="Value" placeholder="011001" type="text" maxlength='6'>
                                        <span id='dac-7-addon' class="input-group-addon">25</span>
                                    </div>
                                </td>
                            </tr>
                            <tr>
                                <th class="text-right">iBiasCalC</th>
                                <td>
                                    <div class="input-group">
                                        <input class="form-control text-right bias" id="DAC-8-input" aria-label="Value" placeholder="010100" type="text" maxlength='6'>
                                        <span id='dac-8-addon' class="input-group-addon">20</span>
                                    </div>
                                </td>
                                <th class="text-right">iBiasRef</th>
                                <td>
                                    <div class="input-group">
                                        <input class="form-control text-right bias" id="DAC-9-input" aria-label="Value" placeholder="001010" type="text" maxlength='6'>
                                        <span id='dac-9-addon' class="input-group-addon">10</span>
                                    </div>
                                </td>
                            </tr>
                            <tr>
                                <th class="text-right">iCbiasP</th>
                                <td>
                                    <div class="input-group">
                                        <input class="form-control text-right bias" id="DAC-10-input" aria-label="Value" placeholder="010010" type="text" maxlength='6'>
                                        <span id='dac-10-addon' class="input-group-addon">18</span>
                                    </div>
                                </td>
                                <th class="text-right">vBiasCasc</th>
                                <td>
                                    <div class="input-group">
                                        <input class="form-control text-right bias" id="DAC-11-input" aria-label="Value" placeholder="001100" type="text" maxlength='6'>
                                        <span id='dac-11-addon' class="input-group-addon">12</span>
                                    </div>
                                </td>
                            </tr>
                            <tr>
                                <th class="text-right">iFbiasN</th>
                                <td>
                                    <div class="input-group">
                                        <input class="form-control text-right bias" id="DAC-12-input" aria-label="Value" placeholder="011000" type="text" maxlength='6'>
                                        <span id='dac-12-addon' class="input-group-addon">24</span>
                                    </div>
                                </td>
                                <th class="text-right">iBiasCalF</th>
                                <td>
                                    <div class="input-group">
                                        <input class="form-control text-right bias" id="DAC-13-input" aria-label="Value" placeholder="000000" type="text" maxlength='6'>
                                        <span id='dac-13-addon' class="input-group-addon">0</span>
                                    </div>
                                </td>
                            </tr>
                            <tr>
                                <th class="text-right">iBiasADC1</th>
                                <td>
                                    <div class="input-group">
                                        <input class="form-control text-right bias" id="DAC-14-input" aria-label="Value" placeholder="100000" type="text" maxlength='6'>
                                        <span id='dac-14-addon' class="input-group-addon">32</span>
                                    </div>
                                </td>
                                <th class="text-right">iBiasADC2</th>
                                <td>
                                    <div class="input-group">
                                        <input class="form-control text-right bias" id="DAC-15-input" aria-label="Value" placeholder="000101" type="text" maxlength='6'>
                                        <span id='dac-15-addon' class="input-group-addon">5</span>
                                    </div>
                                </td>
                            </tr>
                            <tr>
                                <th class="text-right">iBiasAmpLVDS</th>
                                <td>
                                    <div class="input-group">
                                        <input class="form-control text-right bias" id="DAC-16-input" aria-label="Value" placeholder="011010" type="text" maxlength='6'>
                                        <span id='dac-16-addon' class="input-group-addon">26</span>
                                    </div>
                                </td>
                                <th class="text-right">iBiasLVDS</th>
                                <td>
                                    <div class="input-group">
                                        <input class="form-control text-right bias" id="DAC-17-input" aria-label="Value" placeholder="001100" type="text" maxlength='6'>
                                        <span id='dac-17-addon' class="input-group-addon">12</span>
                                    </div>
                                </td>
                            </tr>
                            <tr>
                                <th class="text-right">iBiasPLL</th>
                                <td>
                                    <div class="input-group">
                                        <input class="form-control text-right bias" id="DAC-18-input" aria-label="Value" placeholder="001010" type="text" maxlength='6'>
                                        <span id='dac-18-addon' class="input-group-addon">10</span>
                                    </div>
                                   
                                </td>
                                <th></th>
                                <th></th>
                            </tr>
                        </tbody>
                    </table>
                </div>
                </div>
                <div class="flex-item">
                <div class="table-container">

                    <div class="flex-item">
                        <button id="save-as-vector-file-button" class="btn btn-default" type="button">Save as Vector File</button>
                    </div>
                    <div class="flex-item">
                        <button id="upload-vector-file-button" class="btn btn-default" type="button">Upload Vector File </button>
                    </div>

                </div>
                </div>
                
            </div>
        </div>

        <div class="child">

            <div class="child-header">
                <div id="camera-collapse" class="collapse-button">
                    <div class="collapse-table">
                        <span id="camera-button-symbol" class="collapse-cell    glyphicon glyphicon-triangle-bottom"></span>
                    </div>
                </div>
                <h4>Camera</h4>
            </div>

            <div id="camera-container" class="flex-container">
           
            
                <div id="variable-supply-container" class="flex-item">
                    <div class="child-header-2">
                        <h4 class="non-drop-header">Settings</h4>
                    </div>
                    <div class="table-container-left">` + this.generateResistors(data["resistors"]) + `

                        <div class='well'>Save value as new default on set

                            <div class="btn-group">
                                <button id="save-default-button" type="button" class="btn btn-danger btn-block">OFF</button>
                            </div>
                   
                        </div>

                        <button id="load-default-button" type="button" class="btn btn-primary">Load Default Values</button>
                      
                    </div>

                </div>
            
                <div id="static-supply-container" class="flex-item">
                    <div class="child-header-2">
                        <h4>Monitoring</h4>
                    </div>
                    <div class="table-container">` + this.generateSupplies(data["current_voltage"]) + `
                    </div>
                </div>

            </div>
        </div>
        <div class="child">
            <div class="child-header">
                <div id="operating-collapse" class="collapse-button">
                    <div class="collapse-table">
                        <span id="operating-button-symbol" class="collapse-cell    glyphicon glyphicon-triangle-bottom"></span>
                    </div>
                </div>
                <h4>Operating</h4>
            </div>
                <div id="operating-container" class="flex-container">
                    <div id="adc-calibration-container" class="flex-item">
                        <div class="child-header-2">
                            <h4 class="non-drop-header">ADC Calibration</h4>
                        </div>
                        <div class='table-container-left' id='adc-table'>
                       
                            <div class="input-group" id='adc-input'>
                                <input class="form-control text-right" id="frames-value" placeholder="1" type="text">
                                <span id='frames-addon' class="input-group-addon">Frames</span>
                                <input class="form-control text-right" id="delay-value" placeholder="0" type="text">
                                <span class="input-group-addon">Delay</span>
                            </div>
                            <div class="btn-group">
                                <button id="fine-calibrate-button" type="button" class="btn btn-default">Calibrate Fine</button>
                                <button id="coarse-calibrate-button" type="button" class="btn btn-default">Calibrate Coarse</button>
                                <button id="fine-plot-button" type="button" class="btn btn-default">Plot Fine</button>
                                <button id="coarse-plot-button" type="button" class="btn btn-default">Plot Coarse</button>
                            </div>
                            <div class='row'>
                                <div id='coarse_div' class='column'>
                                    <img id='coarse_graph' class='graph' src='img/coarse_graph.png'>
                                </div>
                                <div id='fine_div' class='column'>
                                    <img id='fine_graph' class='graph' src='img/fine_graph.png'>
                                
                                </div>
                            </div>
                        </div>
                    </div>
          

                </div>
                      




        </div>



    </div>
</div>
`;
    this.mount.appendChild(container);
    document.getElementById("BIAS-collapse").addEventListener("click", this.toggleCollapsed.bind(this, "BIAS"));
    document.getElementById("camera-collapse").addEventListener("click", this.toggleCollapsed.bind(this, "camera"));
    document.getElementById("operating-collapse").addEventListener("click", this.toggleCollapsed.bind(this, "operating"));
    document.getElementById('clock-button').addEventListener("click", this.setClock.bind(this));
    document.getElementById('bp-refresh-button').addEventListener("click", this.update_bp.bind(this));
    document.getElementById('bp-update-button').addEventListener("click", this.updateLoop_bp.bind(this));
    document.getElementById('bp-reload-button').addEventListener("click", this.reload_bp.bind(this));
    this.populateFileList(data["image_vector_files"]["value"], data["adc_vector_files"]["value"]);


    for (i=0; i<data["resistors"].length; i++) {
        document.getElementById("resistor-" + i.toString() + "-button").addEventListener("click", this.setResistor.bind(this, i.toString()));
    };

    document.getElementById('save-default-button').addEventListener("click", this.setVolatile.bind(this));
    document.getElementById('save-as-vector-file-button').addEventListener("click", this.saveAsVector.bind(this));
    document.getElementById('upload-vector-file-button').addEventListener("click", this.uploadVectorPress.bind(this));
    document.getElementById('fine-calibrate-button').addEventListener("click", this.calibrateFine.bind(this));
    document.getElementById('coarse-calibrate-button').addEventListener("click", this.calibrateCoarse.bind(this));

    document.getElementById('fine-plot-button').addEventListener("click", this.plotFine.bind(this));
    document.getElementById('coarse-plot-button').addEventListener("click", this.plotCoarse.bind(this));

    document.getElementById("load-default-button").addEventListener("click", this.load_defaults.bind(this));


    var mode_toggle = document.getElementById('toggle-container');
    var image_vector_files = document.getElementsByClassName("image_vectors")
    var adc_vector_files = document.getElementsByClassName("adc_vectors")
    var mode_toggleContainer = document.getElementById('inner-toggle-container');
    var mode_toggleNumber;
    
    mode_toggle.addEventListener('click', function() {
    mode_toggleNumber = !mode_toggleNumber;
        if (mode_toggleNumber) {
            this.in_calibration_mode = false;
            App.prototype.in_calibration_mode = false;
            for(var i=0; i<image_vector_files.length;i++){
                image_vector_files[i].style.display = 'block';
            }
            for(var i=0; i<adc_vector_files.length;i++){
                adc_vector_files[i].style.display = 'none';
            }
            console.log("in image capture mode")
            console.log(App.prototype.in_calibration_mode)
            mode_toggleContainer.style.clipPath = 'inset(0 0 0 50%)';
            mode_toggleContainer.style.backgroundColor = '#337ab7';
    
        } else {
            this.in_calibration_mode = true;
            App.prototype.in_calibration_mode = true;   
            
            for(var i=0; i<image_vector_files.length;i++){
                image_vector_files[i].style.display = 'none';
            }
            for(var i=0; i<adc_vector_files.length;i++){
                adc_vector_files[i].style.display = 'block';
            }
            console.log("in calibration mode")
            mode_toggleContainer.style.clipPath = 'inset(0 50% 0 0)';
            mode_toggleContainer.style.backgroundColor = '#337ab7';
        }
    });

    var vector_list = document.getElementById("file_list");

    for(var i=0; i< vector_list.children.length; i++){
        vector_list.children[i].addEventListener("click", this.setVectorFile.bind(this));
    }
    
    var bias = document.getElementsByClassName("bias");

    for(var i=0; i < bias.length; i++){
        bias[i].addEventListener("change", this.setDecimalBias.bind(this));
    }


    
    //Update navbar
    var list_elem = document.createElement("li");
    nav_list.appendChild(list_elem);
    var link = document.createElement("a");
    link.href = "#";
    list_elem.appendChild(link);
    var link_text = document.createTextNode("Configuration");
    link.appendChild(link_text);
    link.addEventListener("click", this.changePage.bind(this, "Configuration"));

    document.getElementById("configuration-page").classList.add("active");

    //Add Capture Page
    var container = document.createElement("div");
    container.id = "image-capture-page";
    container.classList.add("adapter-page");
    container.innerHTML = `
        <div id="image-capture-container" class="flex-container">
        <div class ="parent-column" id="image-parent">
            <h4>Image Display</h4>
            <div class="vertical-image" id="image-vertical">

                <div id="image-container">
                    <div id='image-div'>
                        <img id="image_display" src="img/black_img.png? ` + new Date().getTime() + `">
                    </div>
                </div>

                <div class='table-container-left' id='image-buttons'> 
                
                
                    <div class="flex-item">
                        <button id="display-single-button" class="btn btn-default" type="button">Display Single Frame</button>
                        <button id="display-continuous-button" class="btn btn-default" type="button">Stream Images</button>
                        
                       
                    </div>
                    
                    </div>
                
            </div>
        </div>
        

        <div class ="child-column">
            <div class="child">
                <div class="child-header">
                    <div id="capture-collapse" class="collapse-button">
                        <div class="collapse-table">
                            <span id="capture-button-symbol" class="collapse-cell    glyphicon glyphicon-triangle-bottom"></span>
                        </div>
                    </div>
                    <h4>Data Capture</h4>
                </div>
                <div class = "flex-container" id="capture-container">
                    <div class="flex-item">
                        <div id='image-table-left' class = 'table-container-left'>

                            <div class='flex-item'>
                                <div class='input-group input-single'>
                                    <input class="form-control text-right" id="capture-logging-input" placeholder="/scratch/qem/filename" type="text">
                                    <span id='log-file-span' class="input-group-addon addon-single">Filename</span>
                                </div>
                            </div>

                            <div class ='flex-item'>
                                <div class='input-group input-single'>
                                    <input class="form-control text-right" id="capture-fnumber-input" placeholder="1000" type="text">
                                    <span id='frame-num-span' class="input-group-addon addon-single">Number of Frames</span>
                                </div>
                            </div>

                            <div class='flex-item'>
                                <button id="log-run-button" class="btn btn-default" type="button">Save Images</button>
                            </div>
                            
                        </div>
                    </div>
                </div>
            </div>
    
            </div>
        </div>
        </div>
        `;

        this.mount.appendChild(container);
        document.getElementById("capture-collapse").addEventListener("click", this.toggleCollapsed.bind(this, "capture"));
        document.getElementById("display-single-button").addEventListener("click", this.imageGenerate.bind(this));
        document.getElementById("display-continuous-button").addEventListener("click", this.imageGenerateLoop.bind(this));
        //document.getElementById("stop-continuous-button").addEventListener("click", this.stopImageLoop.bind(this));

        document.getElementById("log-run-button").addEventListener("click", this.logImageCapture.bind(this)); 

        //Update navbar
        var list_elem = document.createElement("li");
        nav_list.appendChild(list_elem);
        var link = document.createElement("a");
        link.href = "#";
        list_elem.appendChild(link);
        var link_text = document.createTextNode("Image Capture");
        link.appendChild(link_text);
        link.addEventListener("click", this.changePage.bind(this, "Capture"));

        //add file overlay
        this.file_overlay = document.createElement("div");
        this.file_overlay.classList.add("overlay-background");
        this.file_overlay.classList.add("hidden");
        this.file_overlay.innerHTML = `
            <div class="overlay-freq_file">
            <h5>Save the current bias settings to a new vector file</h5>
            <div>
                <div class="input-group">
                    <input class="form-control text-right" id="file-value" placeholder="" type="text">
                    <span class="input-group-addon">Filename</span>
                </div>
            <div class="overlay-control-buttons">
                    <button class="btn btn-success" id="file-save" type="button">Save</button>
                    <button class="btn btn-danger" id="file-cancel" type="button">Cancel</button>
                </div>
            <div>
            </div>
            `;

       this.mount.appendChild(this.file_overlay);
       document.getElementById("file-cancel").addEventListener("click", this.fileCancel.bind(this));
       document.getElementById("file-save").addEventListener("click", this.createVectorFile.bind(this));

       //Add frequency overlay
       this.freq_overlay = document.createElement("div");
       this.freq_overlay.classList.add("overlay-background");
       this.freq_overlay.classList.add("hidden");
       this.freq_overlay.innerHTML = `
            <div class="overlay-freq_file">
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

        //Add fpga warning overlay
        this.fpga_warn = document.createElement("div");
        this.fpga_warn.classList.add("overlay-background");
        this.fpga_warn.classList.add("hidden");
        this.fpga_warn.innerHTML = `
            <div class="overlay-fpga_warn">
            <h5>Warning:</h5>
            <div>
                <div>
                    <span id = "fpga-warning">This will reprogram the FPGA, click Upload to continue</span>
                </div>
                <div class="overlay-control-buttons" id="fpga-warn-buttons">
                    <button class="btn btn-success" id="upload-vector-final" type="button">Upload</button>
                    <button class="btn btn-danger" id="upload-cancel" type="button">Cancel</button>
                </div>
            </div>
            </div>
            `;

        this.mount.appendChild(this.fpga_warn);
        document.getElementById("upload-cancel").addEventListener("click", this.uploadCancel.bind(this));
        document.getElementById("upload-vector-final").addEventListener("click", this.uploadVector.bind(this));


        this.file_warning = document.createElement("div");
        this.file_warning.classList.add("overlay-background");
        this.file_warning.classList.add("hidden");
        this.file_warning.innerHTML = `
            <div class="overlay-file_warning">
            <h5>Error:</h5>
            <div>
                <div>
                    <span id = "file_warning">Cannot upload, no vector file has been selected.</span>
                </div>
                <div class="overlay-control-buttons" id="file-warning-buttons">
                    <button class="btn btn-danger" id="dismiss-file-warning" type="button">Ok</button>
                </div>
            </div>
            </div>
            `;

        this.mount.appendChild(this.file_warning);
        document.getElementById("dismiss-file-warning").addEventListener("click", this.dismissFileError.bind(this));

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

/*
*   Sleep function to wait n milliseconds
*/
App.prototype.sleep = 
    function(millisec){
        var start = new Date().getTime();
        for (var i = 0; i < 1e7; i++) {
          if ((new Date().getTime() - start) > millisec){
            break;
          }
        }
    }

App.prototype.setDecimalBias =
    function(event){

        var element = event.target;
        var bin_value = element.value;
        dec_value = parseInt(bin_value, 2)
        element.nextElementSibling.innerHTML = dec_value
    
}

/*
* Gets the current coarse calibration graph
* @returns an img tag with the coarse png as the src
*/
App.prototype.generateCoarseGraph = 
    function(){

        document.getElementById('coarse_graph').src = 'img/coarse_graph.png?' + new Date().getTime()
   
        
    }
/*
* Gets the current find calibration graph
* @returns an img tag with the fine png as the src.
*/
App.prototype.generateFineGraph =
    function(){
   
       document.getElementById('fine_graph').src = 'img/fine_graph.png?' + new Date().getTime()

    }


App.prototype.pollForCoarse =
    function(){

        parentthis = this;
        apiGET(parentthis.current_adapter, "coarse_cal_complete").done(
            (function(data){
                console.log(data['coarse_cal_complete'])
                if(data["coarse_cal_complete"] == true){
                    clearInterval(App.prototype.coarse_interval)
                    document.getElementById("coarse-calibrate-button").classList.remove("btn-success")
                    document.getElementById("coarse-calibrate-button").innerHTML = "Calibrate Coarse"
                    document.getElementById("coarse-calibrate-button").classList.add("btn-default")

                    document.getElementById("fine-calibrate-button").disabled = false;
                    document.getElementById("coarse-calibrate-button").disabled = false;
                    //document.getElementById("fine-plot-button").disabled = false;
                    document.getElementById("coarse-plot-button").disabled = false;
                    document.getElementById("log-run-button").disabled = false;
                    document.getElementById("display-single-button").disabled = false;
                    document.getElementById("display-continuous-button").disabled = false;
                }
                
            }).bind(this)
        )
    }
/*
* Performs coarse calibration using the frames and delay value from the webpage
*/  
App.prototype.calibrateCoarse = 
    function(){

        document.getElementById("fine-calibrate-button").disabled = true;
        document.getElementById("coarse-calibrate-button").disabled = true;
        //document.getElementById("fine-plot-button").disabled = true;
        document.getElementById("coarse-plot-button").disabled = true;

        document.getElementById("log-run-button").disabled = true;
        document.getElementById("display-single-button").disabled = true;
        document.getElementById("display-continuous-button").disabled = true;

        document.getElementById("fine-calibrate-button").classList.add("btn-default");
        document.getElementById("fine-calibrate-button").classList.remove("btn-success");
        document.getElementById("coarse-calibrate-button").classList.add("btn-success");
        document.getElementById("coarse-calibrate-button").innerHTML = "Calibrating"
        document.getElementById("coarse-calibrate-button").classList.remove("btn-default");

        var frames = document.getElementById('frames-value').value
        if(frames == ""){
            frames = document.getElementById('frames-value').placeholder
        }
        var delay = document.getElementById('delay-value').value
        if(delay == ""){
            delay = document.getElementById('delay-value').placeholder
        }
        var config = String(frames) + ":" + String(delay)

        apiPUT(this.current_adapter, 'adc_config', config)
        .done(
            apiPUT(this.current_adapter, 'adc_calibrate_coarse', "true")
            .done(
                (function(){

                    App.prototype.coarse_interval = setInterval(this.pollForCoarse.bind(this),500)
  
                }).bind(this)
            )
        )
    }

App.prototype.pollForFine =
    function(){

        parentthis = this;
        apiGET(parentthis.current_adapter, "fine_cal_complete").done(
            (function(data){
                console.log(data['fine_cal_complete'])
                if(data["fine_cal_complete"] == true){
                    clearInterval(App.prototype.fine_interval)
                    document.getElementById("fine-calibrate-button").classList.remove("btn-success")
                    document.getElementById("fine-calibrate-button").innerHTML = "Calibrate Fine"
                    document.getElementById("fine-calibrate-button").classList.add("btn-default")

                    document.getElementById("coarse-calibrate-button").disabled = false;
                    document.getElementById("fine-plot-button").disabled = false;
                    document.getElementById("log-run-button").disabled = false;
                    document.getElementById("display-single-button").disabled = false;
                    document.getElementById("display-continuous-button").disabled = false;
                    document.getElementById("fine-calibrate-button").disabled = false;
                    
                }
                
            }).bind(this)
        )
    }
/*
* Perform coarse calibration using the frames and delay value from the webpage
*/
App.prototype.calibrateFine = 
    function () {

        document.getElementById("coarse-calibrate-button").disabled = true;
        document.getElementById("fine-calibrate-button").disabled = true;
        document.getElementById("fine-plot-button").disabled = true;
        document.getElementById("log-run-button").disabled = true;
        document.getElementById("display-single-button").disabled = true;
        document.getElementById("display-continuous-button").disabled = true;
        

        document.getElementById("fine-calibrate-button").classList.add("btn-success");
        document.getElementById("fine-calibrate-button").classList.remove("btn-default");
        document.getElementById("fine-calibrate-button").innerHTML = "Calibrating"
        document.getElementById("coarse-calibrate-button").classList.add("btn-default");
        document.getElementById("coarse-calibrate-button").classList.remove("btn-success");

        var frames = document.getElementById('frames-value').value
        if(frames == ""){
            frames = document.getElementById('frames-value').placeholder
        }
        var delay = document.getElementById('delay-value').value
        if(delay == ""){
            delay = document.getElementById('delay-value').placeholder
        }
        var config = String(frames) + ":" + String(delay)

        apiPUT(this.current_adapter, 'adc_config', config)
        .done(
            apiPUT(this.current_adapter, 'adc_calibrate_fine', "true")
            .done(
            
                (function(){
                    
                    App.prototype.fine_interval = setInterval(this.pollForFine.bind(this), 500)
       
                }).bind(this)
            )   
        )
    }


App.prototype.pollForPlotFine=
    function(){

        parentthis = this;
        apiGET(parentthis.current_adapter, "fine_plot_complete").done(
            (function(data){
                console.log(data['fine_plot_complete'])
                if(data["fine_plot_complete"] == true){
                    clearInterval(App.prototype.plot_fine_interval)
                    this.generateFineGraph()
                    document.getElementById("fine-plot-button").classList.remove("btn-success")
                    document.getElementById("fine-plot-button").innerHTML = "Plot Fine"
                    document.getElementById("fine-plot-button").classList.add("btn-default")
                    document.getElementById("fine-calibrate-button").disabled = false;
                    document.getElementById("fine-plot-button").disabled = false;
    
                }
                
            }).bind(this)
        )


    }
/*
* Plots all of the fine calibration data and updates the graph on the webpage. 
*/
App.prototype.plotFine = 
    function(){

        document.getElementById("fine-calibrate-button").disabled = true;
        document.getElementById("fine-plot-button").disabled = true;
        document.getElementById("fine-plot-button").classList.add("btn-success");
        document.getElementById("fine-plot-button").innerHTML = "Plotting"
        document.getElementById("fine-plot-button").classList.remove("btn-default");
        document.getElementById("coarse-plot-button").classList.add("btn-default");
        document.getElementById("coarse-plot-button").classList.remove("btn-success");


        apiPUT(this.current_adapter, 'plot_fine', "true").done(
                       
            (function(){
            
                App.prototype.plot_fine_interval = setInterval(this.pollForPlotFine.bind(this), 500)

            }).bind(this)
        )

    }

App.prototype.pollForPlotCoarse=
    function(){

        parentthis = this;
        apiGET(parentthis.current_adapter, "coarse_plot_complete").done(
            (function(data){
                console.log(data['coarse_plot_complete'])
                if(data["coarse_plot_complete"] == true){
                    clearInterval(App.prototype.plot_coarse_interval)
                    this.generateCoarseGraph()
                    document.getElementById("coarse-plot-button").classList.remove("btn-success")
                    document.getElementById("coarse-plot-button").innerHTML = "Plot Coarse"
                    document.getElementById("coarse-plot-button").classList.add("btn-default")
                    document.getElementById("coarse-calibrate-button").disabled = false;
                    document.getElementById("coarse-plot-button").disabled = false;
    
                }
                
            }).bind(this)
        )

    }

App.prototype.plotCoarse = 
    function(){

        document.getElementById("coarse-calibrate-button").disabled = true;
        document.getElementById("coarse-plot-button").disabled = true;
        document.getElementById("coarse-plot-button").classList.add("btn-success");
        document.getElementById("coarse-plot-button").classList.remove("btn-default");
        document.getElementById("coarse-plot-button").innerHTML = "Plotting"
        document.getElementById("fine-plot-button").classList.add("btn-default");
        document.getElementById("fine-plot-button").classList.remove("btn-success");


        apiPUT(this.current_adapter, 'plot_coarse', "true").done(
                       
            (function(){
                App.prototype.plot_coarse_interval = setInterval(this.pollForPlotCoarse.bind(this), 500)
            }).bind(this)
        )

    }
/*
* Generates the resistor table using the data passed from the backplane
* @param resistors : the data['resistors'] list from the backplane 
* @returns the resistor table html tag
*/
App.prototype.generateResistors =
    function (resistors) {
        resistor_table = `
        <table>
            <thead>
              <tr>
                <th></th>
                <th>Resistance</th>
              </tr>
            </thead>
            <tbody>`
        var i;
        for (i=0; i<resistors.length; i++) {
            resistor_table += `
              <tr>
                <th class="text-right">` + resistors[i]["name"] + `</th>
                <td>
                  <div class="input-group">
                    <input class="form-control text-right" id="resistor-`+ i.toString() +`-input" aria-label="Value" placeholder="` + Number(resistors[i]["resistance"]["value"]).toFixed(2).toString() + `" type="text">
                    <span class="input-group-addon">` 
                    
                    var str = resistors[i]["resistance"]["units"]
                    if (str.length == 1) {
                        str += "  "
                    }
                    resistor_table += str +`</span>
                    <div class="input-group-btn">
                      <button class="btn btn-default" id="resistor-`+ i.toString() + `-button" type="button">Set</button>
                    </div>
                  </div>
                </td>
              </tr>`
        }
        resistor_table += `
            </tbody>
        </table>`
        return resistor_table
    };

/*
* Generates the variable supply table using the data passed from the backplane
* @param supplies: the data["current_voltage"]) list from the backplane
* @returns the supply table html tag.
*/
App.prototype.generateSupplies =
    function (supplies) {
        supply_table = `
        <table>
            <thead>
              <tr>
                <th></th>
                <th>Voltage (V)</th>
                <th>Current (mA)</th>
              </tr>
            </thead>
            <tbody>`
        var i;
        for (i=0; i<supplies.length; i++) {
            supply_table += `
              <tr>
                <th class="text-right">` + supplies[i]["name"] + `</th>
                <td>
                  <span id="supply-voltage-`+ i.toString() + `">` + Number(supplies[i]["voltage"]["value"]).toFixed(3).toString() + `</span>
                </td>
                <td>
                  <span id="supply-current-`+ i.toString() + `">` + Number(supplies[i]["current"]["value"]).toFixed(2).toString() + `</span>
                </td>
              </tr>`
        }
        supply_table += `
            </tbody>
        </table>`
        return supply_table
    };

App.prototype.pollForDefaults =
    function(){

        parentthis = this;
        apiGET(parentthis.current_adapter, "defaults_loaded").done(
            (function(data){
                console.log(data['defaults_loaded'])
                if(data["defaults_loaded"] == true){
                    clearInterval(App.prototype.defaults_interval)
                    this.reload_bp()
                }
                
            }).bind(this)
        )
    }

App.prototype.load_defaults = 
    function(){


        apiPUT(this.current_adapter, "load_defaults", "true").done(
            (function(){

                    App.prototype.defaults_interval = setInterval(this.pollForDefaults.bind(this), 100)
                   

            }).bind(this)
        )



    }

/*
* Sets whether the backplane is constantly updating the values or not
*/
App.prototype.updateLoop_bp =
    function() {
        var button = document.getElementById('bp-update-button')
        if (button.innerHTML=="Disabled") {
            apiPUT(this.current_adapter, "sensors_enabled", "true");
            this.update_bp();
            button.innerHTML="Updating";
            button.classList.remove("btn-danger");
            button.classList.add("btn-success");
            document.getElementById('bp-refresh-button').disabled = true;
        } else {
            apiPUT(this.current_adapter, "sensors_enabled", "false");
            button.innerHTML="Disabled";
            button.classList.remove("btn-success");
            button.classList.add("btn-danger");
            document.getElementById('bp-refresh-button').disabled = false;
        }
    }
/*
* updates the variable supplies table by requesting the whole adapter paramtree
* populates the table and repeats if enabled.
*
*/
App.prototype.update_bp =
    function() {
        apiPUT(this.current_adapter, "update_required", "true")
        .done(
            (function() {
                apiGET(this.current_adapter, "", false)
                .done(
                    //console.log(data)
                    (function(data) {
                        for (i=0; i<data["current_voltage"].length; i++) {
                            document.getElementById('supply-voltage-' + i.toString()).innerHTML = Number(data["current_voltage"][i]["voltage"]).toFixed(3).toString();
                            document.getElementById('supply-current-' + i.toString()).innerHTML = Number(data["current_voltage"][i]["current"]).toFixed(2).toString();
                        }
                        if (data["sensors_enabled"]=="True") {
                            setTimeout(this.update_bp.bind(this), this.update_delay * 1000);
                        }
                    }).bind(this)
                )
                .fail(this.setError.bind(this));
            }).bind(this)
        )
    }

// opens the fpga warning overlay when "upload vector file" is pressed
App.prototype.uploadVectorPress = 
    function(){
        var text_file = document.getElementById("current-txt-file").innerHTML
        if(text_file == ""){
            this.file_warning.classList.remove("hidden")
        }
        else{
            this.fpga_warn.classList.remove("hidden");
        }
}

App.prototype.dismissFileError = 
    function(){
        this.file_warning.classList.add("hidden");
    }

//closes the fpga warning overlay when cancel is pressed.
App.prototype.uploadCancel = 
    function(){
        this.fpga_warn.classList.add("hidden");
    
    }

//opens the save vector file overlay when 'save as vector file' is pressed
App.prototype.saveAsVector = 
    function(){
        document.getElementById("file-value").placeholder = "QEM_D4_198_ADC_10_icbias1_ifbias1";
        this.file_overlay.classList.remove("hidden");
    }

//closes the save vector file overlay when cancel is pressed
App.prototype.fileCancel = 
    function(){
        document.getElementById("file-value").value = "";
        this.file_overlay.classList.add("hidden");
    }

App.prototype.pollForFileWritten = 
    function(){

        parentthis = this;
        apiGET(parentthis.current_adapter, "vector_file_written").done(
            (function(data){
                console.log(data['vector_file_written'])
                if(data["vector_file_written"] == true){
                    clearInterval(App.prototype.file_written_interval)
                    document.getElementById('save-as-vector-file-button').innerHTML= "File Saved"
                    
                    this.updateFileList()
                    
                  
                    setTimeout(function(){
                        document.getElementById('save-as-vector-file-button').innerHTML= "Save as Vector File"
                        document.getElementById("save-as-vector-file-button").classList.add("btn-default");
                        document.getElementById("save-as-vector-file-button").classList.remove("btn-success");
                        
                    }, 3000)
                    
                }
                
            }).bind(this)
        )



    }

/*
* Generates a vector file from the current BIAS settings in the webpage
* closes the save as vector file overlay when the file is created
*/
App.prototype.createVectorFile = 
    function(){

        document.getElementById('save-as-vector-file-button').innerHTML= "Saving File"
        document.getElementById("save-as-vector-file-button").classList.add("btn-success");
        document.getElementById("save-as-vector-file-button").classList.remove("btn-default");
        

        var filename = document.getElementById("file-value").value;
        document.getElementById("current-txt-file").innerHTML = filename

        console.log(filename)
  
        if (App.prototype.in_calibration_mode == true && !filename.includes("ADC")){
          
            extension = filename.substr(-4)
            if (extension == ".txt"){
               file_name = filename.substr(0, filename.length-4)
               filename = file_name + "_ADC" + extension
            }
            console.log(filename)
        }
        else if (App.prototype.in_calibration_mode == false && !filename.includes("IMG")){
            
            extension = filename.substr(-4)
            if (extension == ".txt"){
               file_name = filename.substr(0, filename.length-4)
               filename = file_name + "_IMG" + extension
            }
            console.log(filename)
        }

        console.log(filename)


        apiPUT(this.current_adapter, "update_bias", "false")
        .done(
            (function(){
                apiPUT(this.current_adapter, "vector_file", filename)
                .done(
                    (function(){
                        for(i=0; i < 19; i++){
                            var value = document.getElementById("DAC-"+ i.toString() + "-input").value;
                            
                            apiPUT(this.current_adapter, "dacs/" + i.toString() + "/value", value.toString())
                            
                        }

                        App.prototype.file_written_interval = setInterval(this.pollForFileWritten.bind(this), 100)
                    }).bind(this)
                )
            }).bind(this)
        )
        document.getElementById("file-value").value = "";
        this.file_overlay.classList.add("hidden");
    }

App.prototype.pollForUploadComplete = 
    function(){
        parentthis = this;
        apiGET(parentthis.current_adapter, "upload_vector_complete").done(
            (function(data){
                console.log(data['upload_vector_complete'])
                if(data["upload_vector_complete"] == true){
                    clearInterval(App.prototype.upload_vector_interval)
                    document.getElementById("upload-vector-file-button").innerHTML = "Vector File Uploaded"
                    document.getElementById("coarse-calibrate-button").disabled = false;
                    document.getElementById("fine-calibrate-button").disabled = false;
                    document.getElementById("fine-plot-button").disabled = false;
                    document.getElementById("coarse-plot-button").disabled = false;
                    document.getElementById("log-run-button").disabled = false;
                    document.getElementById("display-single-button").disabled = false;
                    document.getElementById("display-continuous-button").disabled = false;
                    document.getElementById("upload-vector-file-button").disabled = false;
                    setTimeout(function(){
       
                        document.getElementById("upload-vector-file-button").innerHTML = "Upload Vector File"
                        document.getElementById("upload-vector-file-button").classList.remove("btn-success")
                        document.getElementById("upload-vector-file-button").classList.add("btn-default")

                    
                    }, 3000)
            
    
                }
                
            }).bind(this)
        )
    }
/*
* Sends the command to the asic to upload the current vector file
* Closes the fpga warning overlay when complete.
*/
App.prototype.uploadVector = 
    function(){


        apiPUT(this.current_adapter, "fpga_reset", "true").done(
            
            (function(){
            
                console.log("returned done from fpga reset")
                document.getElementById("coarse-calibrate-button").disabled = true;
                document.getElementById("fine-calibrate-button").disabled = true;
                document.getElementById("fine-plot-button").disabled = true;
                document.getElementById("coarse-plot-button").disabled = true;
                document.getElementById("log-run-button").disabled = true;
                document.getElementById("display-single-button").disabled = true;
                document.getElementById("display-continuous-button").disabled = true;
                document.getElementById("upload-vector-file-button").disabled = true;

                //this.sleep(2000)
                this.fpga_warn.classList.add("hidden");
        
                apiPUT(this.current_adapter, "upload_vector_file", "true")
                .done(
                    (function(){
                        document.getElementById("upload-vector-file-button").classList.remove("btn-default")
                        document.getElementById("upload-vector-file-button").classList.add("btn-success")
                        document.getElementById("upload-vector-file-button").innerHTML = "Uploading Vector File"
                        App.prototype.upload_vector_interval = setInterval(this.pollForUploadComplete.bind(this), 250)
                    }).bind(this)
                )
            }).bind(this)

        )

    }

/*
* Runs an update of the API to get the new image and adc vector files.
* Calls populateFileList and regenerates the list of adc and image vector files in the dropdown 
*/    
App.prototype.updateFileList = 
    function(){
        
        apiGET(this.current_adapter, "", false)
        .done(
            (function(data){
                this.populateFileList(data["image_vector_files"], data["adc_vector_files"])
            }).bind(this)

        )
}

/*
* populates the list of image and adc vector files in the dropdown menu
* @param image_files: data['image_vector_files'] list of vector files in dev08
* @param adc: data['adc_vector_files'] list of vector files in dev08
*/
App.prototype.populateFileList = 
    function(image_files, adc_files) {
        
        var the_list = document.getElementById('file_list')
        var file_list = '';
        var i;
        for (i=0; i<image_files.length; i++) {
            file_list += '<li id="image_files" class="image_vectors"><a href="#">' + image_files[i] + '</a></li>';
        }

        var j;
        for (j=0; j<adc_files.length; j++) {
            file_list += '<li class="adc_vectors"><a href="#">' + adc_files[j] + '</a></li>';
        }
        the_list.innerHTML = file_list;

}

/*
* Reloads the backplane updating the resistors and variable supplies 
* calls the update_bp method
*/
App.prototype.reload_bp =
    function() {
        apiPUT(this.current_adapter, "reset", "true")
        .done(
            (function() {
                apiGET(this.current_adapter, "", false)
                .done(
                    //console.log(data)
                    (function(data) {
                        apiPUT(this.current_adapter, "clock", parseFloat(document.getElementById('clock-input').placeholder));
                        for (i=0; i<data["resistors"].length; i++) {
                            document.getElementById('resistor-' + i +  '-input').placeholder=Number(data["resistors"][i]["resistance"]).toFixed(2).toString()
                        };
                        this.update_bp();
                    }).bind(this)
                )
                .fail(this.setError.bind(this));
            }).bind(this)
        )
    }

/* 
* Sets the clock on the backplane using the clock-input from the webpage
*/
App.prototype.setClock =
    function() {
        var element = document.getElementById('clock-input');
        var value = Number(element.value);
        apiPUT(this.current_adapter, "clock", value)
        .done(
            function() {
                element.placeholder = value.toFixed(1)
                element.value = ""
            }
        )
        .fail(this.setError.bind(this))
    }


App.prototype.pollForVectorSet = 
    function(){

        parentthis = this;
        apiGET(parentthis.current_adapter, "bias_parsed").done(
            (function(data){
                console.log(data['bias_parsed'])
                if(data["bias_parsed"] == true){

                    clearInterval(App.prototype.set_vector_interval)
                    apiGET(this.current_adapter, "", false)
                    .done(
                        function(data){
                            for(i=0; i< data["dacs"].length; i++){
                                document.getElementById('DAC-' + i.toString() + '-input').value = data["dacs"][i]["value"];
                                document.getElementById("dac-" + i.toString() + "-addon").innerHTML = parseInt(data["dacs"][i]["value"], 2)
                            }
                        }
                    )
                }
                
            }).bind(this)
        )


    }
/*
* Sets the current vector file being used by the asic using the one selected on the drop-down 
* Retrieves all of the bias settings from the vector file used and populates the bias 
* settings on the webpage
*/
App.prototype.setVectorFile = 
    function(event){

        var element = event.target
        var value = element.innerHTML

        document.getElementById("current-txt-file").innerHTML = value

        apiPUT(this.current_adapter, "update_bias", "true")
        .done(
            apiPUT(this.current_adapter, "vector_file", value)
            .done( 
                (function(){

                    App.prototype.set_vector_interval = setInterval(this.pollForVectorSet.bind(this), 150)
       
                }).bind(this)
            )
            .fail(this.setError.bind(this))
        ).fail(this.setError.bind(this))
    };

/*
* Sets the resistnce of a given resistor number on the backplane
* @param number: the number resistor to set 
*/
App.prototype.setResistor =
    function(number) {
        var element = document.getElementById('resistor-' + number +  '-input');
        var location = "resistors/" + number + "/resistance"
        var value = Number(element.value);
        apiPUT(this.current_adapter, location, value)
        .done(
            function() {
                element.placeholder = value.toFixed(2)
                element.value = ""
            }
        )
        .fail(this.setError.bind(this))
    }

/*
* Sets whether to use volatile memory when setting the resistor values
* This would then cause that resistor value to be a default value. 
*/
App.prototype.setVolatile =
    function() {
        var button = document.getElementById('save-default-button')
        if (button.innerHTML=="OFF") {
            apiPUT(this.current_adapter, "non_volatile", "true");
            this.update_bp();
            button.innerHTML="ON";
            button.classList.remove("btn-danger");
            button.classList.add("btn-success");
        } else {
            apiPUT(this.current_adapter, "non_volatile", "false");
            button.innerHTML="OFF";
            button.classList.remove("btn-success");
            button.classList.add("btn-danger");
        }
    }

App.prototype.updateImage = 
    function(){
        this.sleep(100)
        document.getElementById('image_display').src = "img/current_image.png?" + new Date().getTime()    
    }

App.prototype.pollForImage = 
    function(now){
        parentthis = this;
        apiGET(parentthis.current_adapter, "image_ready").done(
            (function(data){
                console.log(data['image_ready'])
                if(data["image_ready"] == true){
                    parentthis.updateImage()
                    clearInterval(App.prototype.image_interval)
                }
               
            }).bind(this)
        )
    }

App.prototype.imageGenerate =
    function() {

        apiPUT(this.current_adapter, "image", 2)
        .done(
            (function(single){            
                App.prototype.image_interval = setInterval(this.pollForImage.bind(this), 100)

            }).bind(this)
        ).fail(this.setError.bind(this));
    }

App.prototype.imageGenerateLoop = 
    function(){

        //console.log("image loop")
        document.getElementById("fine-calibrate-button").disabled = true;
        document.getElementById("coarse-calibrate-button").disabled = true;

        var button = document.getElementById('display-continuous-button')

        document.getElementById("log-run-button").disabled = true;
        document.getElementById("display-single-button").disabled = true;
        
        if(button.innerHTML  == "Stream Images"){
            //console.log("button = safe")
            button.innerHTML = "Stop Streaming Images"
            button.classList.remove("btn-default")
            button.classList.add("btn-danger")
            this.imageGenerate()
            App.prototype.image_loop_interval = setInterval(this.imageGenerate.bind(this), 350)
        }
        else if (button.innerHTML == "Stop Streaming Images"){
            //console.log("button = strop")
            button.classList.add("btn-default")
            button.classList.remove("btn-danger")
            button.innerHTML = "Stream Images"
            this.stopImageLoop()
            document.getElementById("fine-calibrate-button").disabled = false;
            document.getElementById("coarse-calibrate-button").disabled = false;
        }
 
}

App.prototype.stopImageLoop = 
    function(){

        clearInterval(App.prototype.image_interval)
        clearInterval(App.prototype.image_loop_interval)
        document.getElementById("log-run-button").disabled = false;
        document.getElementById("display-single-button").disabled = false;
   
    }


App.prototype.pollForLogComplete =
function (){
    parentthis = this;
    apiGET(parentthis.current_adapter, "log_complete").done(
        (function(data){
            console.log(data['log_complete'])
            if(data["log_complete"] == true){
                
                clearInterval(App.prototype.log_file_interval)
                document.getElementById("log-run-button").innerHTML = "Images Saved"
                document.getElementById("display-continuous-button").disabled = false;
                document.getElementById("display-single-button").disabled = false;

                setTimeout(function(){
                    document.getElementById("log-run-button").classList.remove("btn-success");
                    document.getElementById("log-run-button").classList.add("btn-default");
                    document.getElementById("log-run-button").innerHTML = "Save Images"
                }, 3000)
            }
           
        }).bind(this)
    )
 
}

App.prototype.logImageCapture =
    function() {

        document.getElementById("log-run-button").classList.add("btn-success");
        document.getElementById("log-run-button").classList.remove("btn-default");
        document.getElementById("log-run-button").innerHTML = "Saving Images"
        document.getElementById("display-continuous-button").disabled = true;
        document.getElementById("display-single-button").disabled = true;

        var fnumber = Number(document.getElementById('capture-fnumber-input').value)
        if (fnumber == ""){
            fnumber = Number(document.getElementById('capture-fnumber-input').placeholder)
        }
        var location = String(document.getElementById('capture-logging-input').value)
        if (location == ""){
            var d = new Date()
            var date = d.getDay() + "-" + d.getMonth() + "-" + d.getFullYear()
            location = String(document.getElementById('capture-logging-input').placeholder) + date
        }

        apiPUT(this.current_adapter, "capture_run", fnumber.toString() + ";" + location)
        .done(
            (
                function(){
                    //document.getElementById("log-run-button").innerHTML = "Saving Images"
                    App.prototype.log_file_interval = setInterval(this.pollForLogComplete.bind(this), 100)

                }
            ).bind(this)
        )
    }

App.prototype.calibrationImageCapture =
    function() {
        var location = String(document.getElementById('calibration-logging-input').value)
        var Vstart = Number(document.getElementById('configure-input-start').value).toFixed(2)
        var Vstep = Number(document.getElementById('configure-input-step').value).toFixed(2)
        var Vfinish = Number(document.getElementById('configure-input-finish').value).toFixed(2)
        this.calibrationImageCaptureStep("1000;" + location, Vstart, Vstep, Vfinish)
    }

App.prototype.calibrationImageCaptureStep =
    function(configuration, VStart, VStep, VFinish) {
        parentthis = this;
        apiPUT(parentthis.current_adapter, "resistors/6/resistance", VStart)
        .done(
            (function() {
                setTimeout(function() {
                    apiPUT(parentthis.current_adapter, "capture_run", configuration + "_" + VStart.toString())
                    .done(
                        function() {
                            VStart = (VStart + VStep).toFixed(2);
                            if (VStart <= VFinish) {
                                parentthis.calibrationImageCaptureStep(configuration, VStart, VStep, VFinish);
                            }
                        }
                    )
                    .fail(parentthis.setError.bind(this))
                }, 50);
            })
        )
        .fail(parentthis.setError.bind(this))
    }

/*
* Changes the current page viewed on the webpage between configuration and image capture
* @param page: the page to change to the active page
*/
App.prototype.changePage =
    function(page) {
        if(page=="Configuration") {
            document.getElementById("configuration-page").classList.add("active");
            document.getElementById("image-capture-page").classList.remove("active");
        } else {
            document.getElementById("configuration-page").classList.remove("active");
            document.getElementById("image-capture-page").classList.add("active");
        }
    };

/*
* Collapses the given section from view 
* @param section : the container section to collapse
*
*/    
App.prototype.toggleCollapsed =
    function(section) {
        document.getElementById(section + "-container").classList.toggle("collapsed");
        document.getElementById(section + "-button-symbol").classList.toggle("glyphicon-triangle-right");
        document.getElementById(section + "-button-symbol").classList.toggle("glyphicon-triangle-bottom");
    };

/*
* Parses any given error from the json data and calls showError with the content
*/
App.prototype.setError =
    function(data) {
        if(data.hasOwnProperty("json")) {
            var json = data.responseJSON;
            if(json.hasOwnProperty("error"))
                this.showError(json.error);
        } else {
            this.showError(data.responseText);
        }
    }

/*
* Shows the error message (msg) in the top error bar
* @param msg: the error message content to display
*/
App.prototype.showError =
    function(msg) {
        if(this.error_timeout !== null) clearTimeout(this.error_timeout);
        this.error_message.nodeValue = `Error: ${msg}`;
        this.error_timeout = setTimeout(this.clearError.bind(this), 5000);
    }

App.prototype.clearError =
    function() {
        this.error_message.nodeValue = "";
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
    function() {
        this.dark_mode = !this.dark_mode;
        this.setCookie("dark", this.dark_mode.toString());

        this.mount.classList.toggle("dark");
        this.documentBody.classList.toggle("background-dark");
    };

App.prototype.getCookie =
    function(key)  {
        var raw = document.cookie.split(';');
        for(var value of raw) {
            if(value.indexOf(key) == 0)
                return decodeURIComponent(value.substring(key.length + 1));
        }
    };

App.prototype.setCookie =
    function(key, value) {
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
            if(raw[i].indexOf(key) === 0) {
                raw[i] = cookieString;
                found = true;
            }
        if(!found)
            raw.push(cookieString);
        var s = `${raw.join(';')};${expires};path=/`;
        document.cookie = `${raw.join(';')};${expires};path=/`;
    };

//Create the App() instance
function initApp() {
    var app = new App();
}

