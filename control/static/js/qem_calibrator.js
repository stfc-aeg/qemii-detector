$(document).ready(function() {
    console.log("QEM CALIBRATOR LOADED");
});

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