/* Vector File Manager and Manipulation
 * For the QEMII camera system.
 * Read, write, and upload vector files.
 * 
 * Adam Neaves, Applicaiton Engineering Group, STFC. 2019
 */

 var selected_vector_file = 'None Selected';
 var bias_names;

$(document).ready(function() {
    console.log("VECTOR FILE MANAGER LOADED");
    $('#mdl-vector-save').on("show.bs.modal", function(){
        console.log("Modal Shown");
        var file_string = selected_vector_file.replace("QEM_", "");
        file_string = file_string.replace(".txt", "");
        $('#txt-vector-save-name').val(file_string);
    });

    get_vector_file();
    getFileName();
    getVectorBiases();
    get_vector_file_list();
});

function interface_set_disable(disabled)
{
    console.log("Interface Enabled: " + !disabled);
    for(var key in bias_names)
    {
        var txt = $('#txt_' + key);
        txt.attr("disabled", disabled);
    }
    $('#btn-select-vector').attr("disabled", disabled);
    $('#btn-save-vector').attr("disabled", disabled);
    $('#btn-reset-vector').attr("disabled", disabled);
    $('#btn-load-vector').attr("disabled", disabled);
    
}

function getVectorBiases(){
    console.log("Get Vector File Bias");
    $.getJSON('/api/' + api_version + "/qem_detector/fems/fem_0/vector_file/bias", function(response){
        bias_names = response.bias;
        var table_body = $('#tbl-body-bias');
        // delete all current rows
        table_body.empty();
        for(var key in bias_names){
            var value = bias_names[key];
            console.log(key + ": " + value);
            row = biasTableRow(key, value);
            table_body.append(row);

        }
    });
}

function biasTableRow(name, val){

    var txt_name = "txt_" + name;
    var bin_val = get_binary_string(val);

    //create all needed elements
    var row = document.createElement("tr");
    var name_col = document.createElement("td");
    var val_col = document.createElement("td");
    var txt_box = document.createElement("input");
    var form_div = document.createElement("div");
    var form_lbl = document.createElement("label");
    var name_div = document.createElement("div");


    form_lbl.setAttribute("for", txt_name);
    form_div.setAttribute("class", "form-group");
    
    txt_box.setAttribute("id", txt_name);
    txt_box.setAttribute("value", val);
    txt_box.setAttribute("type", "number");
    txt_box.setAttribute("min", "0");
    txt_box.setAttribute("max", "63");

    
    name_col.setAttribute("class", "col-md-6");
    val_col.setAttribute("class", "col-md-6");
    form_lbl.setAttribute("id", "lbl_" + name);

    form_div.appendChild(txt_box);
    form_div.appendChild(form_lbl);
    name_col.appendChild(name_div);
    row.appendChild(name_col);
    row.appendChild(val_col);

    txt_box.classList.add("form-control");
    txt_box.addEventListener("change", function(){
        set_bias_val(name, txt_box.value);
    });
    txt_box.addEventListener("keyup", function(event){
        //keycode 13 is the enter key
        if(event.keyCode === 13){
            event.preventDefault();
            set_bias_val(name, txt_box.value);
        }
    });

    val_col.appendChild(form_div);
    form_lbl.innerHTML = bin_val;
    name_div.innerHTML = "<p>" + name + "</p>";
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
    interface_set_disable(true);
    $.ajax({
        type: "PUT",
        url: '/api/' + api_version +'/qem_detector/fems/fem_0/vector_file',
        contentType: "application/json",
        data: JSON.stringify({"file_name": selected_vector_file})
    }).done(
        function(){
            getVectorBiases();
            interface_set_disable(false);
        }
    )
}

function get_vector_file(){
    $.getJSON('/api/' + api_version +'/qem_detector/fems/fem_0/vector_file/file_name', function(response){
        selected_vector_file = response.file_name;
        console.log(selected_vector_file);
        $('#btn-select-vector').html(selected_vector_file + '<span class="caret"></span>');
    });
}

function upload_vector_file(){
    console.log("Uploading " + selected_vector_file);
    interface_set_disable(true);
    $.ajax({
        type: "PUT",
        url: '/api/' + api_version +'/qem_detector/fems/fem_0/',
        contentType: "application/json",
        data: JSON.stringify({"load_vector_file": "default"})
    }).done(
        interface_set_disable(false)
    )
}

function set_bias_val(bias, val){
    console.log("Setting Bias " + bias + " to: " + val);
    var dict = {};
    dict[bias] = parseInt(val);
    $.ajax({
        type: "PUT",
        url: '/api/' + api_version +'/qem_detector/fems/fem_0/vector_file/bias',
        contentType: "application/json",
        data: JSON.stringify(dict)
    }).done(
        function(){
            
            bin_val = get_binary_string(val);
            console.log("Changing lbl_" + bias + " to " + bin_val);
            lbl_name = "lbl_" + bias;
            lbl = document.getElementById(lbl_name);
            lbl.innerHTML = bin_val;
        }
    )
}

function get_binary_string(val){
    int_val = parseInt(val);
    return "000000".substr(int_val.toString(2).length) + int_val.toString(2);
}

function save_vector_file(file_name){
    if(!file_name.startsWith("QEM_")){
        file_name = "QEM_" + file_name;
    }
    if(!file_name.endsWith(".txt")){
        file_name = file_name + ".txt";
    }
    console.log("Saving Vectors as " + file_name);
    selected_vector_file = file_name;
    $.ajax({
        type: "PUT",
        url: '/api/' + api_version +'/qem_detector/fems/fem_0/vector_file/',
        contentType: "application/json",
        data: JSON.stringify({"save": file_name})
    }).done(
        function(){
            get_vector_file_list();
            $('#btn-select-vector').html(selected_vector_file + ' <span class="caret"></span>');
            $('#mdl-vector-save').modal('hide');
        }
    )
}

function reset_vector_file(){
    console.log("Resetting vectors to file: " + selected_vector_file);
    $.ajax({
        type: "PUT",
        url: '/api/' + api_version +'/qem_detector/fems/fem_0/vector_file/',
        contentType: "application/json",
        data: JSON.stringify({"reset": ""})
    }).done(
        function(){
            getVectorBiases();
            $('#mdl-vector-reset').modal('hide');
        }
    )
}