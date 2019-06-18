api_version = '0.1';
file_write_name = 'None';
file_write_enabled = false;
$( document ).ready(function() {

    update_api_version();
    update_api_adapters();
    get_vector_file();
    getFileName();
    getVectorBiases();

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
