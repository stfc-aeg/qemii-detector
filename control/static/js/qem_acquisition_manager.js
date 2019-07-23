var acq_path = '/api/0.1/qem_detector/acquisition/'
$( document ).ready(function() {
    getNumberFrames();
    getFrameGap();
});


function getNumberFrames(){
    $.getJSON(acq_path + "num_frames", function(response){
        num_frames = response.num_frames;
        console.log("Number of Frames: " + num_frames);
        $('#txt-num-frames').val(num_frames);
    });
}

function setNumberFrames(){
    num_frames = $('#txt-num-frames').val();
    $.ajax({
        type: "PUT",
        url: acq_path,
        contentType: "application/json",
        data: JSON.stringify({"num_frames": num_frames})
    });
}

function getFrameGap(){
    $.getJSON(acq_path + "frame_gap", function(response){
        frame_gap = response.frame_gap;
        console.log("Frame Gap: " + frame_gap);
        $('#txt-frame-gap').val(frame_gap);
    });
}

function setFrameGap(){
    frame_gap = $('#txt-frame-gap').val();
    $.ajax({
        type: "PUT",
        url: acq_path,
        contentType: "application/json",
        data: JSON.stringify({"frame_gap": frame_gap})
    });
}

function setAcquisitionConfig(){
    console.log("Setting Acquisition Configuration");
    frame_gap = parseInt($('#txt-frame-gap').val());
    num_frames = parseInt($('#txt-num-frames').val());
    console.log("Number Frames: " + num_frames + ", Frame Gap:" + frame_gap);
    $.ajax({
        type: "PUT",
        url: acq_path,
        contentType: "application/json",
        data: JSON.stringify({"frame_gap": frame_gap,
                              "num_frames": num_frames})
    });

    file_name = $('#txt-file-name').val();
    console.log("Setting File name to " + file_name)
    $.ajax({
        type: "PUT",
        url: '/api/' + api_version +'/qem_detector/daq/file_info/',
        contentType: "application/json",
        data: JSON.stringify({"file_name": file_name})
    });
}

function startAcquisition(){
    console.log("Starting Acquisition");
    $.ajax({
        type: "PUT",
        url: acq_path,
        contentType: "application/json",
        data: JSON.stringify({"start_acq": "Data"})
    })
}