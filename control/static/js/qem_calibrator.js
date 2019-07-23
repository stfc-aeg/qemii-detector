$(document).ready(function() {
    console.log("QEM CALIBRATOR LOADED");
    check_calibration_flag();
    check_plot_flag();

});

function start_calibrate_coarse(){
    console.log("Starting Coarse Calibration");
    set_calibrate_interface_disable(true);
    $.ajax({
        type: "PUT",
        url: '/api/' + api_version +'/qem_detector/calibrator/',
        contentType: "application/json",
        data: JSON.stringify({"start_calibrate": "coarse"})
    }).done(
        function(){
            set_label(true, "Calibration");
            check_calibration_flag();
        }
    )
}

function start_calibrate_fine(){
    console.log("Starting Fine Calibration");
    set_calibrate_interface_disable(true);
    $.ajax({
        type: "PUT",
        url: '/api/' + api_version +'/qem_detector/calibrator/',
        contentType: "application/json",
        data: JSON.stringify({"start_calibrate": "fine"})
    }).done(
        function(){
            set_label(true, "Calibration");
            check_calibration_flag();
        }
    )
}

function start_plot_coarse(){
    console.log("Starting Coarse Plot");
    set_calibrate_interface_disable(true);
    $.ajax({
        type: "PUT",
        url: '/api/' + api_version +'/qem_detector/calibrator/',
        contentType: "application/json",
        data: JSON.stringify({"start_plot": "coarse"})
    }).done(
        function(){
            set_label(true, "Plot");
            check_plot_flag();
        }
    )
}

function start_plot_fine(){
    console.log("Starting Fine Plot");
    set_calibrate_interface_disable(true);
    $.ajax({
        type: "PUT",
        url: '/api/' + api_version +'/qem_detector/calibrator/',
        contentType: "application/json",
        data: JSON.stringify({"start_plot": "fine"})
    }).done(
        function(){
            set_label(true, "Plot");
            check_plot_flag();
        }
    )
}

function check_calibration_flag(){

    $.getJSON('/api/' + api_version +'/qem_detector/calibrator/', function(response){
        var current_val = response.calibrator.calibration_vals.current;
        var max_val = response.calibrator.calibration_vals.max - 1;
        var progress_percent = (current_val / max_val) *100;
        if(progress_percent < 100 && progress_percent != 0){ //if 0, the calibration isn't currently running
            $('#prg-calibrate-progress').attr("style", "width: " + progress_percent +"%");
            $('#prg-calibrate-progress').html(Math.round(progress_percent) + "%");

            set_label(true, "Calibration");
            set_calibrate_interface_disable(true);
            window.setTimeout(check_calibration_flag, 100);
            
        }else{
            console.log("Calibration Complete");
            set_label(false, "Calibration");
            set_calibrate_interface_disable(false);
        }
    });
}

function check_plot_flag(){
    $.getJSON('/api/' + api_version +'/qem_detector/daq/in_progress', function(response){
        if(response.in_progress == true){
            set_label(true, "Plot");
            set_calibrate_interface_disable(true);
            window.setTimeout(check_plot_flag, 100);
        }else{
            console.log("Plot Complete");
            set_label(false, "Plot");
            set_calibrate_interface_disable(false);
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

function set_calibrate_interface_disable(disabled) {
    $('#btn-cal-coarse').attr("disabled", disabled);
    $('#btn-cal-fine').attr("disabled", disabled);
    $('#btn-plot-coarse').attr("disabled", disabled);
    $('#btn-plot-fine').attr("disabled", disabled);
}