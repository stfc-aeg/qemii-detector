api_version = '0.1';
selected_vector_file = 'None Selected';
file_write_name = 'None';
file_write_enabled = false;
$( document ).ready(function() {

    update_api_version();
    update_api_adapters();
    get_vector_file();
    getFileName();

    $('#write-enabled').bootstrapSwitch();
    $('#write-enabled').on('switchChange.bootstrapSwitch', function(event, state){
        changeWriteState(state);
    });
   
});

function update_api_version() {

    $.getJSON('/api', function(response) {
        $('#api-version').html(response.api);
        api_version = response.api;
    });
}

function update_api_adapters() {

    $.getJSON('/api/' + api_version + '/adapters/', function(response) {
        adapter_list = response.adapters.join(", ");
        $('#api-adapters').html(adapter_list);
    });
}

function get_vector_file_list() {
    $.getJSON('/api/' + api_version + '/file_interface/vector_files', function(response) {
        var ul = $('#lst-vector-files');
        ul.empty();
        var list = response.vector_files;
        console.log(list);
        var calibrate_list = [];
        var image_list = [];
        for(var item = 0; item < list.length; item++){
            var file = list[item];
            if(file.includes("ADC")){
                calibrate_list.push(file);
            }else{
                image_list.push(file);
            }
            //ul.append('<li><a class="dropdown-item"href="#">'+ list[item] + '</a></li>')
        }
        ul.append('<li class="dropdown-header">Calibration Vector Files</li>')
        for(var cal_item = 0; cal_item < calibrate_list.length; cal_item++){
            ul.append('<li><a class="dropdown-item"href="#">'+ calibrate_list[cal_item] + '</a></li>')
        }
        ul.append('<li class="dropdown-header">Image Capture Vector Files</li>')
        for(var img_item = 0; img_item < image_list.length; img_item++){
            ul.append('<li><a class="dropdown-item"href="#">'+ image_list[img_item] + '</a></li>')
        }

        ul.children().click(function(event){
            selected_vector_file = $(event.target).html();
            $('#btn-select-vector').html(selected_vector_file + ' <span class="caret"></span>');
            set_vector_file();
        })
    });
}

function set_vector_file() {
    $.ajax({
        type: "PUT",
        url: '/api/' + api_version +'/qem_detector/fems/fem_0/',
        contentType: "application/json",
        data: JSON.stringify({"selected_vector_file": selected_vector_file})
    }).done(
        function(){
            $('#btn-load-vector').removeClass('btn-success');
            $('#btn-load-vector').removeClass("disabled");
            $('#btn-load-vector').disabled = false;
            $('#btn-load-vector').addClass('btn-primary');
            $('#btn-load-vector').html("Upload vector File");
        }
    )

}

function get_vector_file(){
    $.getJSON('/api/' + api_version +'/qem_detector/fems/fem_0/selected_vector_file', function(response){
        selected_vector_file = response.selected_vector_file;
        console.log(selected_vector_file);
        $('#btn-select-vector').html(selected_vector_file + '<span class="caret"></span>');
    });
}

function upload_vector_file(){
    console.log("Uploading " + selected_vector_file);
    $.ajax({
        type: "PUT",
        url: '/api/' + api_version +'/qem_detector/fems/fem_0/',
        contentType: "application/json",
        data: JSON.stringify({"load_vector_file": "default"})
    }).done(
        function(){
            $('#btn-load-vector').removeClass("btn-primary");
            $('#btn-load-vector').addClass("btn-success");
            $('#btn-load-vector').addClass("disabled");
            $('#btn-load-vector').disabled = true;
            $('#btn-load-vector').html("Vector File Uploaded");
        }
    )
}

function start_calibrate_coarse(){
    console.log("Starting Coarse Calibration");
    $.ajax({
        type: "PUT",
        url: '/api/' + api_version +'/qem_detector/calibrator/',
        contentType: "application/json",
        data: JSON.stringify({"start_coarse_calibrate": "true"})
    }).done(
        function(){
            set_label(true, "Calibration");
            check_calibration_flag();
        }
    )
}

function start_calibrate_fine(){
    console.log("Starting Fine Calibration");
    $.ajax({
        type: "PUT",
        url: '/api/' + api_version +'/qem_detector/calibrator/',
        contentType: "application/json",
        data: JSON.stringify({"start_fine_calibrate": "true"})
    }).done(
        function(){
            set_label(true, "Calibration");
            check_calibration_flag();
        }
    )
}

function start_plot_coarse(){
    console.log("Starting Coarse Plot");
    $.ajax({
        type: "PUT",
        url: '/api/' + api_version +'/qem_detector/calibrator/',
        contentType: "application/json",
        data: JSON.stringify({"start_coarse_plot": "true"})
    }).done(
        function(){
            set_label(true, "Plot");
            check_plot_flag();
        }
    )
}

function start_plot_fine(){
    console.log("Starting Fine Plot");
    $.ajax({
        type: "PUT",
        url: '/api/' + api_version +'/qem_detector/calibrator/',
        contentType: "application/json",
        data: JSON.stringify({"start_fine_plot": "true"})
    }).done(
        function(){
            set_label(true, "Plot");
            check_plot_flag();
        }
    )
}

function check_calibration_flag(){
    $.getJSON('/api/' + api_version +'/qem_detector/calibrator/calibration_complete', function(response){
        if(response.calibration_complete == false){
            window.setTimeout(check_calibration_flag, 100);
        }else{
            console.log("Calibration Complete");
            set_label(false, "Calibration"); 
        }
    });
}

function check_plot_flag(){
    $.getJSON('/api/' + api_version +'/qem_detector/calibrator/plot_complete', function(response){
        if(response.plot_complete == false){
            window.setTimeout(check_plot_flag, 100);
        }else{
            console.log("Plot Complete");
            set_label(false, "Plot");
            //refresh graphs
            coarse_graph = $('#coarse-graph');
            fine_graph = $('#fine-graph');
            coarse_graph.attr('src', coarse_graph.attr("data-src") + "?t=" + Date.now());
            fine_graph.attr('src', fine_graph.attr("data-src") + "?t=" + Date.now());
        }
    });
}

function set_label(in_progress, label_type){
    if(label_type =="Calibration"){
        var label = $('#lbl-calibrate');
    }else if(label_type == "Plot"){
        var label = $('#lbl-plot');
    }else{
        return;
    }

    if(in_progress){
        label.removeClass("label-success");
        label.addClass("label-danger");
        label.html(label_type + ": In Progress");
    }else{
        label.removeClass("label-danger");
        label.addClass("label-success");
        label.html(label_type + ": Not in Progress"); 
    }
}

function changeWriteState(state){
    console.log("Changing Write State to: " + state);
    $.ajax({
        type: "PUT",
        url: '/api/' + api_version +'/qem_detector/file_info/',
        contentType: "application/json",
        data: JSON.stringify({"file_write": state})
    });
}

function getFileName(){
    $.getJSON('/api/' + api_version +'/qem_detector/file_info/file_name', function(response){
        file_write_name = response.file_name;
        txt_box = $('#txt-file-name');
        console.log(file_write_name);
        txt_box.val(file_write_name);
        console.log("Textbox Value: " + txt_box.val());
    });
}

function setFileName(){
    file_name = $('#txt-file-name').val();
    console.log("Setting File name to " + file_name)
    $.ajax({
        type: "PUT",
        url: '/api/' + api_version +'/qem_detector/file_info/',
        contentType: "application/json",
        data: JSON.stringify({"file_name": file_name})
    });
}

function checkFileName(){
    txt_box = $('#txt-file-name');
    btn = $('#btn-reset-file-name');
    if(file_write_name === txt_box.val()){
        btn.disabled = true;
        btn.addClass("disabled");
    }
    else
    {
        btn.disabled = false;
        btn.removeClass("disabled");
    }
}