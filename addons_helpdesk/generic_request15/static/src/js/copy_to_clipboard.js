odoo.define('generic_request15.copy_commit_to_clipboard', function (require) {
"use static";

var Widget = require('web.Widget');

var _copyToClipboard = function (event) {
    var caseElement = document.querySelector('.case_id_class');

    if (caseElement.firstChild != null) {
        var caseValue = caseElement.firstChild.nodeValue;

        navigator.clipboard.writeText(caseValue).then(function() {
          /* clipboard successfully set */
        }, function() {
          /* clipboard write failed */
        });
    }
}

$(document).on('click', '.copy_case_id_class', _copyToClipboard);

var CopyToClipboard = Widget.extend({});
});
