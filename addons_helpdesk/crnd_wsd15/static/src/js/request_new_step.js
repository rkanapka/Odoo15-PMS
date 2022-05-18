odoo.define('crnd_wsd15.request_new_step', function (require) {
    'use strict';

    var snippet_animation = require('website.content.snippets.animation');
    var snippet_registry = snippet_animation.registry;

    var RequestNewStep = snippet_animation.Class.extend({
        selector: 'form.wsd-request-new-select-param',

        events: {
            'click a.request-new-btn-back': '_onClickBack',
        },

        start: function () {
            var self = this;

            // Handle on click on item when layout is tiles
            if (self.$target.data('layout') === 'tiles') {
                self.$target.find(
                    '.wsd-request-new-select-param-item input'
                ).on('click', function () {
                    self.$target.submit();
                });
            }
        },

        _onClickBack: function () {
            window.history.back();
        },
    });

    snippet_registry.RequestNewStep = RequestNewStep;

});
