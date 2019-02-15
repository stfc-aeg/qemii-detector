function Button(app, meta)
{
    Component.call(this, app, meta);
}

Button.use =
    function(meta)
    {
        return Component.utils.isLeaf(meta)
            && meta.type === "bool"
            && meta.writeable;
    };

Button.prototype = new Component();

Button.prototype.oldValue = false;
Button.prototype.buttonElem = null;

Button.prototype.update =
    function(data)
    {
        if(data === this.oldValue) return;

        this.oldValue = data;
        if(this.meta.name === "Update Once")
        {
            if(data)
            {
                this.buttonElem.disabled = true;
                this.buttonElem.childNodes[0].nodeValue = "Updating";
            }
            else
            {
                this.buttonElem.disabled = false;
                this.buttonElem.childNodes[0].nodeValue = "Update";
            }
        }
        else if(this.meta.name != "Reset Server")       
        {
            if(data)
            {
                this.buttonElem.classList.remove("btn-danger");
                this.buttonElem.classList.add("btn-success");
                this.buttonElem.childNodes[0].nodeValue = "Disable";
            }
            else
            {
                this.buttonElem.classList.remove("btn-success");
                this.buttonElem.classList.add("btn-danger");
                this.buttonElem.childNodes[0].nodeValue = "Enable";
            }
        }
    };

Button.prototype.generate =
    function()
    {
        if(this.meta.name === "Update Once")
        {
            var ret = `
<button id="${this.getID()}" type="button" class="btn btn-default"`;
            if(this.meta.hasOwnProperty("description"))
            {
                ret += `title="${this.meta.description}"`;
            }
            ret += `>Update</button>`;
        }
        else if(this.meta.name === "Reset Server")
        {
            var ret = `
<button id="${this.getID()}" type="button" class="btn btn-default"`;
            if(this.meta.hasOwnProperty("description"))
            {
                ret += `title="${this.meta.description}"`;
            }
            ret += `>Reset</button>`;
        }
        else if(this.meta.name === "Reset FPGA")                            
        {                                                                     
            var ret = `                                                       
<button id="${this.getID()}" type="button" class="btn btn-default"`;          
            if(this.meta.hasOwnProperty("description"))                       
            {                                                                 
                ret += `title="${this.meta.description}"`;                    
            }                                                                 
            ret += `>Reset</button>`;                                         
        }                                                                     
        else
        {
            var ret = `
<button id="${this.getID()}" type="button" class="btn btn-toggle btn-danger"`;
            if(this.meta.hasOwnProperty("description"))
            {
                ret += `title="${this.meta.description}"`;
            }
            ret += `>Enable</button>`;
        }
        return ret;
    };

Button.prototype.init =
    function()
    {
        this.buttonElem = document.getElementById(this.getID());
        this.buttonElem.addEventListener("click", this.onClick.bind(this));
    };

Button.prototype.onClick =
    function()
    {
        this.app.put(this.getPath(), !this.oldValue);
    };

Component.registerComponent(Button);
