window.addEventListener("load", function() {
    var inputselect = document.getElementById("inputselect");
    var iriinput = document.getElementById("iriinput");
    var textinput = document.getElementById("textinput");
    var videorow = document.getElementById("videorow");
    var theform = document.getElementById("theform");

    function update_form (inputtype) {
        if (inputtype === "iri") {
            iriinput.style.display = "inline";
            textinput.style.display = "none";
            videorow.style.display = "table-row";
            theform.method = "get";
        } else if (inputtype == "yt") {
            iriinput.style.display = "inline";
            textinput.style.display = "none";
            videorow.style.display = "none";
            theform.method = "get";
        } else { // inputtype === "text"
            iriinput.style.display = "none";
            textinput.style.display = "inline";
            videorow.style.display = "table-row";
            theform.method = "post";
        }
    }
    update_form(inputselect.value); // ensure correct layout after reload

    inputselect.addEventListener("change", function(event) {
        update_form(event.target.value);
    }, false);

    document.getElementById("example1").addEventListener("click", function(event) {
        textinput.value = 'WEBVTT\n' +
            '\n' +
            'cue1\n' +
            '00:00:00.000 --> 00:00:12.000\n' +
            '{\n' +
            '  "@context": "http://bit.ly/1cNnqfL",\n' +
            '  "tags": ["wind scene", "opening credits"],\n' +
            '  "contributors": ["http://ex.org/sintel"]\n' +
            '}';
        document.getElementById("inputselect").value =
            "text";
        update_form("text");
    }, false);
    
    document.getElementById("example2").addEventListener("click", function(event) {
        document.getElementById("iriinput").value =
            "http://champin.net/2014/linkedvtt/demonstrator-metadata.vtt";
        document.getElementById("context").value =
            "http://champin.net/2014/linkedvtt/demonstrator-context.json";
        document.getElementById("inputselect").value =
            "iri";
        update_form("iri");
    }, false);


}, false);
