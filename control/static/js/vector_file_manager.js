/* Vector File Manager and Manipulation
 * For the QEMII camera system.
 * Read, write, and upload vector files.
 * 
 * Adam Neaves, Applicaiton Engineering Group, STFC. 2019
 */

 selected_vector_file = 'None Selected';

$(document).ready(function() {
    console.log("VECTOR FILE MANAGER LOADED");
});

function getVectorBiases(){
    console.log("Get Vector File");
    $.getJSON('/api/' + api_version + "/qem_detector/fems/fem_0/vector_file/bias", function(response){
        biases = response.bias;
        table_body = $('#tbl-body-bias');
        for(var key in biases){
            value = biases[key];
            console.log(key + ": " + value);
            row = biasTableRow(key, value);
            table_body.append(row);

        }
    });
}

function biasTableRow(name, val){
    var row = document.createElement("tr");
    var name_col = document.createElement("td");
    var val_col = document.createElement("td");

    row.appendChild(name_col);
    row.appendChild(val_col);

    bin_val = val.toString(2);
    val_col.innerHTML = "000000".substr(bin_val.length) + bin_val;
    name_col.innerHTML = name;

    return row;

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