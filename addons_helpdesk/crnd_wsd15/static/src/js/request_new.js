odoo.define('crnd_wsd15.new_request', function (require) {
    'use strict';

    // Require Trumbowyg to be loaded.
    var trumbowyg = require('crnd_wsd15.trumbowyg');
    var snippet_animation = require('website.content.snippets.animation');
    var snippet_registry = snippet_animation.registry;

    var blockui = require('crnd_wsd15.blockui');

    var RequestCreateWidget = snippet_animation.Class.extend({
        selector: '#form_request_text',

        events: {
            'click a.request-new-btn-back': '_onClickBack',
        },

        start: function () {
            var self = this;
            self.req_max_size = self.$target.closest(
                '#wrap.crnd-wsd-wrap').data('max_text_size');

            self.load_editor();
            self.visual_characters_left_textarea();
            self.$target.submit(function () {
                blockui.blockUI();
            });

        },

        visual_characters_left_textarea: function () {
            var self = this;
            if (self.req_max_size) {
                var request_body = self.$target.find('#request-body');
                self.check_textarea();
                request_body.on(
                    'keydown', 'div', self.check_textarea.bind(self));
                request_body.on(
                    'keyup', 'div', self.check_textarea.bind(self));
                request_body.on(
                    'paste', 'div', self.check_textarea.bind(self));
            }
        },

        check_textarea: function () {
            var self = this;
            var request_text_size = self.$target.find(
                '#request_text').val().replace(/(<([^>]+)>)/ig, '').length;
            var $span_label = $('#characters_left_label');
            var left_input = self.req_max_size - request_text_size;
            var percent = left_input / self.req_max_size;
            $span_label.tooltip();
            if (left_input < 0) {
                left_input = 0;
            }

            if (percent >= 0.2) {

                $span_label.removeClass("badge-warning badge-danger");
                $span_label.addClass("badge-primary");

            } else if (percent < 0.2 && percent > 0.1) {

                $span_label.removeClass("badge-primary badge-danger");
                $span_label.addClass("badge-warning");

            } else {

                $span_label.removeClass("badge-primary badge-warning");
                $span_label.addClass("badge-danger");
            }

            $span_label.html(left_input + " / " + self.req_max_size);
        },

        load_editor: function () {
            this.$form_request_text = this.$target.find('#request_text');
            this.$form_request_text.trumbowyg(trumbowyg.trumbowygOptions);
        },

        _onClickBack: function () {
            window.history.back();
        },
    });

    snippet_registry.RequestCreateWidget = RequestCreateWidget;

    return {
        RequestCreateWidget: RequestCreateWidget,
    };

});
