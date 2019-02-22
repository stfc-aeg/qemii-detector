api_version = '0.1';

$( document ).ready(function() {

    update_api_version();
    update_api_adapters();
    //poll_update()
});

/*
function poll_update() {
    update_background_task();
    setTimeout(poll_update, 500);   
}
*/
function update_api_version() {

    $.getJSON('/api', function(response) {
        $('#api-version').html(response.api_version);
        api_version = response.api_version;
    });
}

function update_api_adapters() {

    $.getJSON('/api/' + api_version + '/adapters/', function(response) {
        adapter_list = response.adapters.join(", ");
        $('#api-adapters').html(adapter_list);
    });
}

function update_background_task() {

    $.getJSON('/api/' + api_version + '/workshop/background_task', function(response) {
        var task_count = response.background_task.count;
        var task_enabled = response.background_task.enable;
        $('#task-count').html(task_count);
        $('#task-enable').prop('checked', task_enabled);
    });
}

function change_enable() {
    var enabled = $('#task-enable').prop('checked');
    console.log("Enabled changed to " + (enabled ? "true" : "false"));
    $.ajax({
        type: "PUT",
        url: '/api/' + api_version + '/workshop/background_task',
        contentType: "application/json",
        data: JSON.stringify({'enable': enabled})
    });
}

function set_file_name(){

}

function set_file_path(){

}

function load_fp_config_file(){

    $.getJSON('/api/' + api_version + '/workshop/fp_config_files', function(response) {
        var ul = $('#fp_file_list');
        ul.empty();
        var list = response.fp_config_files;
        for(var item = 0; item < list.length; item++){
            ul.append('<li><a class="dropdown-item" href="#">' + list[item] + '</a></li>');
        
        }
        ul.children().click(function(event){
            var value = $(event.target).html()
            $('#current-processor-file').html(value);
            set_fp_file();
        })
       
    });
 
}

function load_fr_config_file(){

    $.getJSON('/api/' + api_version + '/workshop/fr_config_files', function(response) {
        var ul = $('#fr_file_list');
        ul.empty();
        var list = response.fr_config_files;
        for(var item = 0; item < list.length; item++){
            ul.append('<li><a class="dropdown-item"href="#">'+ list[item] + '</a></li>');
           
        }
        ul.children().click(function(event){
            var value = $(event.target).html()
            $('#current-receiver-file').html(value);
            set_fr_file();
        })

        
    });

}

function set_fp_file(){
    var file = $('#current-processor-file').html();
    console.log(file);
    $.ajax({
        type: "PUT",
        url: '/api/' + api_version + '/fp/config/config_file',
        contentType: "application/json",
        data: JSON.stringify("/aeg_sw/work/projects/qem/qem-ii/install/config/" + file)
    });
    
}

function set_fr_file(){
    var file = $('#current-receiver-file').html();
    $.ajax({
        type: "PUT",
        url: '/api/' + api_version + '/fr/config/config_file',
        contentType: "application/json",
        data: JSON.stringify("/aeg_sw/work/projects/qem/qem-ii/install/config/" + file)
    });
}

function start_filewriter(){

    var file_path = $("#file-path").val();
    if(file_path == ""){
        console.log("file path is empty")
        file_path = "/tmp";
    }
    var file_name = $("#file-name").val();
    if(file_name == ""){
        console.log("file name is empty")
        var time = JSON.stringify(new Date());
        file_name = "qemii_data_" + time;
    }

    $.ajax({
        type: "PUT",
        url: '/api/' + api_version + '/fp/config/hdf/file/path',
        contentType: "application/json",
        data: JSON.stringify(file_path)
    }).done(
        function(){
            $.ajax({
                type: "PUT",
                url: '/api/' + api_version + '/fp/config/hdf/file/name',
                contentType: "application/json",
                data: JSON.stringify(file_path)
            }).done(
                function(){
                    $.ajax({
                        type: "PUT",
                        url: '/api/' + api_version + '/fp/config/hdf/write',
                        contentType: "application/json",
                        data: JSON.stringify(true)
                    })
                }
            );
        }
    )
    

    $("#file-badge").removeClass("label-danger");
    $("#file-badge").addClass("label-success");
    $("#file-badge").html("File Writer Enabled")
    
}

function stop_filewriter(){
    $("#file-badge").removeClass("label-success");
    $("#file-badge").addClass("label-danger");
    $("#file-badge").html("File Writer Disabled")
    $.ajax({
        type: "PUT",
        url: '/api/' + api_version + '/fp/config/hdf/file/write',
        contentType: "application/json",
        data: JSON.stringify(false)
    })
}
