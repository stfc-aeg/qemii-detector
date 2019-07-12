var liveview_enable = false;
var clip_enable = false;
var autosize_enable = true;
var clip_slider = null;
var size_slider = null;
var api_url = '/api/0.1/live_view/';
var img_elem = null;
var img_scaling = 1.0;

var img_start_time = new Date().getTime();
var img_end_time = null;
var img_pol_freq = 1;


$(document).ready(function() {
    console.log("Live View Manager Loading");
    

    img_elem = $('#liveview_image');
    img_elem.load(function()
    {
        var img_end_time = new Date().getTime();
        resizeImage();
        var load_time = img_end_time - img_start_time;

        if(liveview_enable)
        {
            if(img_pol_freq - load_time < 0)
            {
                updateImage();
            }
            else
            {
                setTimeout(updateImage, img_pol_freq - load_time);
            }
            if(load_time < img_pol_freq)
            {
                $('#liveview-fps-lbl').innerHTML = (1000 / img_pol_freq).toFixed(2) + "Hz";
            }
            else
            {
                $('#liveview-fps-lbl').innerHTML = (1000 / load_time).toFixed(2) + "Hz";
            }
        }
    });

    $('#liveview-enable-chk').bootstrapSwitch();
    $('#liveview-enable-chk').bootstrapSwitch('state', liveview_enable, true);
    $('#liveview-resize-chk').bootstrapSwitch();
    $('#liveview-resize-chk').bootstrapSwitch('state', autosize_enable, true);
    $('#liveview-clipping-chk').bootstrapSwitch();
    $('#liveview-clipping-chk').bootstrapSwitch('state', clip_enable, true);
    
    // Configure clipping range slider
    clip_slider = $("#clip-range").slider({});
    size_slider = $('#size-range').slider({});

    size_slider.on('slideStop', changeSizeEvent);
    size_slider.slider(!autosize_enable ? "enable" : "disable");

    $('#liveview-enable-chk').on('switchChange.bootstrapSwitch', function(event, state){
        changeLiveViewEnable();
    });
    $('#liveview-resize-chk').on('switchChange.bootstrapSwitch', function(event, state){
        changeAutosizeEnable();
    });

    buildColormapSelect();
});


function buildColormapSelect()
{
    console.log("Getting Live View Colourmap Options");
    $.getJSON('/api/' + api_version + "/live_view/", function(response){
        var colormap_options = response.colormap_options;
        selected_colormap = response.colormap_selected;
        console.log("Selected Colormap: " + selected_colormap)
        var dropdown_list = $('#lst-liveview-colourmaps');
        dropdown_list.empty();
        var dropdown_button = $('#liveview-colourmap-drp')
        // var colormaps_sorted = Object.keys(colormap_options).sort();
        
        for(key in colormap_options){
            var value = colormap_options[key];
            console.log("Colormap Option: " + key + ": " + value);
            var list_item = document.createElement("li");
            var button = document.createElement("a");
            
            button.setAttribute("class", "dropdown-item");
            button.setAttribute("key", key);
            button.innerHTML = value;
            // list_item.innerHTML = '<a class="dropdown-item" href="#" key=' + key + '>' + value + '</a>';
            if(key == selected_colormap){
                list_item.setAttribute("class", "active")
                dropdown_button.html("Selected Map: " + value + '<span class="caret"></span>');
            }
            list_item.append(button);
            dropdown_list.append(list_item);

            list_item.addEventListener('click', function(event){
                selected_colormap = $(event.target).attr('key');
                console.log("Selected: " + selected_colormap);
                $.ajax({
                    type: "PUT",
                    url: api_url,
                    contentType: "application/json",
                    data: JSON.stringify({"colormap_selected": selected_colormap})
                }).done(function(){
                    child_list = dropdown_list.children();
                    for(var i = 0; i< child_list.length; i++){
                        var element = $(child_list[i]);
                        // console.log(element);
                        element.removeClass("active");
                    }
                    $(event.target).parent().addClass("active");
                    dropdown_button.html("Selected Map: " + $(event.target).html() + ' <span class="caret"></span>');
                })
                
            });
        }
    });
}

function changeLiveViewEnable()
{
    liveview_enable = $("#liveview-enable-chk").bootstrapSwitch('state');
    console.log("Live View Enable changed to: " + liveview_enable)
    if(liveview_enable)
    {
        updateImage();
    }
};

function changeAutosizeEnable()
{
    autosize_enable = $("#liveview-resize-chk").bootstrapSwitch('state');
    console.log("Autosize Enabled: " + autosize_enable);
    size_slider.slider(!autosize_enable ? "enable" : "disable");
    resizeImage();
};

function changeSizeEvent(size_event)
{
    var new_size = size_event.value;
    console.log("New size: " + new_size);
    img_scaling = new_size / 100;
    resizeImage();
};

function updateImage()
{
    img_start_time = new Date().getTime();
    img_elem.attr("src", img_elem.attr("data-src") + '?' +  new Date().getTime());

    $.getJSON(api_url + "data_min_max", function(response)
    {
        updateClipRange(response.data_min_max, !clip_enable);
    });
};

function resizeImage()
{

    var img_width = img_elem.prop('naturalWidth');
    // console.log("Image Dims: [" + img_width + ", " + img_height + "]");
    if (autosize_enable) {

        var img_container_width =  $("#live-image-container").width();
        // var img_container_height = $("#live-image-container").height();

        var width_scaling = Math.min(img_container_width / img_width, 1.0);
        // var height_scaling = Math.min(img_container_height / img_height, 1.0);

        
        size_slider.data('slider').setValue(Math.floor(width_scaling * 100));
    }

    img_elem.width(img_scaling*img_width);
    img_elem.height('auto');

};

function updateClipRange(data_min_max, reset_current=false)
{
    var data_min = parseInt(data_min_max[0]);
    var data_max = parseInt(data_min_max[1]);

    $('#clip_min').text(data_min);
    $('#clip_max').text(data_max);

    var current_values = clip_slider.data('slider').getValue();

    if (reset_current) {
        current_values = [data_min, data_max]
    }

    // clip_slider.slider('setAttribute', 'max', data_max);
    // clip_slider.slider('setAttribute', 'min', data_min);
    clip_slider.slider('setAttribute', 'ticks', [data_min, data_max]);
    clip_slider.slider('setAttribute', 'ticks_labels', [data_min, data_max]);
    clip_slider.slider('refresh');
    clip_slider.slider('setValue', current_values);
}