odoo.define('web.widgets.api_m2o_widget', function (require) {
    "use strict";

    var field_registry = require('web.field_registry');
    var field_utils = require('web.field_utils');
    var FieldMany2One = require('web.relational_fields').FieldMany2One;


    function _get_record_field (record, field_name) {
        if (record._changes && record._changes[field_name]) {
            return record._changes[field_name];
        }
        return record.data[field_name];
    }

    // Modify basic model with extra methods to fetch special data
    var BasicModel = require('web.BasicModel');
    BasicModel.include({
        _readUngroupedList: function (list) {
            var self = this;
            var def = this._super.apply(this, arguments);
            return def.then(function () {
                return $.when(self._fetchApiM2OsBatched(list));
            }).then(function () {
                return list;
            });
        },
        _fetchApiM2OsBatched: function (list) {
            var defs = [];
            var fieldNames = list.getFieldNames();
            for (var i = 0; i < fieldNames.length; i++) {
                var fieldName = fieldNames[i];
                var fieldInfo = list.fieldsInfo[list.viewType][fieldName];
                if (fieldInfo.widget === 'api_m2o') {
                    defs.push(this._fetchApiM2OBatched(list, fieldName));
                }
            }
            return $.when.apply($, defs);
        },
        _fetchApiM2OBatched: function (list, fieldName) {
            var self = this;
            var wlist = this._applyX2ManyOperations(list);
            var defs = [];

            var fieldInfo = wlist.fieldsInfo[wlist.viewType][fieldName];
            _.each(wlist.data, function (dataPoint) {
                var record = self.localData[dataPoint];
                defs.push(
                    $.when(
                        self._fetchApiM2O(
                            record,
                            fieldName,
                            fieldInfo.model_field)
                    ).then(function (specialData) {
                        record.specialData[fieldName] = specialData;
                    })
                );
            });
            return $.when.apply($, defs);
        },
        _fetchSpecialApiM2O: function (record, fieldName, fieldInfo) {
            var field = record.fields[fieldName];
            if (field.type === 'integer' ||
                    field.type === 'many2one_reference') {
                return this._fetchApiM2O(
                    record, fieldName, fieldInfo.model_field);
            }
            return $.when();
        },
        _fetchApiM2O: function (record, fieldName, model_field) {
            var self = this;

            var model = _get_record_field(record, model_field);
            var res = _get_record_field(record, fieldName);

            if (model && model !== 'False' && res) {
                var resID = null;
                if (typeof res.id === 'undefined') {
                    resID = res;
                } else {
                    resID = res.id;
                }

                if (resID) {
                    return self._rpc({
                        model: model,
                        method: 'exists',
                        args: [resID],
                        context: record.getContext({fieldName: fieldName}),
                    }).then(function (existant_records) {
                        return self._rpc({
                            model: model,
                            method: 'name_get',
                            args: [existant_records],
                            context: record.getContext({fieldName: fieldName}),
                        }).then(function (result) {
                            if (result.length >= 1) {
                                return self._makeDataPoint({
                                    data: {
                                        id: result[0][0],
                                        display_name: result[0][1],
                                    },
                                    modelName: model,
                                    parentID: record.id,
                                });
                            }
                            return self._makeDataPoint({
                                data: {
                                    id: 0,
                                    display_name: undefined,
                                },
                                modelName: model,
                                parentID: record.id,
                            });
                        });
                    });
                }
            }
            return $.when();
        },
    });


    // Define new ApiM2O field widget
    var FieldApiM2O = FieldMany2One.extend( {
        resetOnAnyFieldChange: true,
        supportedFieldTypes: ['integer', 'many2one_reference'],
        specialData: "_fetchSpecialApiM2O",
        template: "FieldMany2One",

        init: function () {
            this._super.apply(this, arguments);

            // Configure widget options
            this.limit = 0;
            this.limit_result = (this.attrs.limit_result)? parseInt(this.attrs.limit_result) : this.SEARCH_MORE_LIMIT;

            this.can_create = false;
            this.can_write = false;
            this.nodeOptions.quick_create = false;

            this.value = this.record.specialData[this.name];
            this.m2o_value = this._formatValue(this.value);

            this.model_field = this.attrs.model_field;

            // Needs to be copied as it is an unmutable object
            this.field = _.extend({}, this.field);

            this._update_field_relation();
        },

        _update_field_relation: function () {
            if (this.record._changes) {
                this.field.relation = this.record._changes[this.model_field];
            } else {
                this.field.relation = this.record.data[this.model_field];
            }
            return this.field.relation;
        },
        _formatValue: function (value) {
            if (value === 0) {
                return '';
            }

            var val = this.record.specialData[this.name];
            if (val && val.data && val.data.display_name) {
                return val.data.display_name;
            }
            return '';
        },
        _parseValue: function (value) {
            if ($.isNumeric(value) && Number.isInteger(value)) {
                return value;
            }
            return field_utils.parse.integer(
                value, this.field, this.parseOptions);
        },
        _setValue: function (value, options) {
            var val = value.id;
            return this._super(val, options);
        },

        // @Override core function _manageSearchMore
        _manageSearchMore: function (values, search_val, domain, context) {
            var self = this;

            Object.assign(
                context,
                {
                    'search_more': true,
                    'limit_result': self.limit_result
                }
            );

            values = values.slice(0, this.limit);
            values.push({
                // label: "Search More...",
                label: "Select Interface Data...",
                action: function () {
                    var prom = self._rpc({
                            model: self.field.relation,
                            method: 'name_search',
                            kwargs: {
                                args: domain,
                                limit: self.limit_result,
                                context: context,
                            },
                        });
                    Promise.resolve(prom).then(function (results) {
                        var dynamicFilters;
                        var ids = false
                        if (results) {
                            ids = _.map(results, function (x) {
                                return x[0];
                            });
                        }
                        if (search_val !== '') {
                            dynamicFilters = [{
                                description: _.str.sprintf('Quick search: %s', search_val),
                                domain: [['name', 'ilike', search_val]],
                            }];
                        }
                        self._searchCreatePopup("search", ids, {}, dynamicFilters);
                    });
                },
                classname: 'o_m2o_dropdown_option',
            });
            return values;
        },

        // _search: function () {
        //     this._update_field_relation();
        //     return this._super.apply(this, arguments);
        // },
        // @Override core function _search
        _search: async function (searchValue = "") {
            this._update_field_relation();

            const value = searchValue.trim();
            const context = Object.assign(
                this.record.getContext(this.recordParams),
                this.additionalContext
            );
            // const context = this.record.getContext(this.recordParams);

            // const domain = this.record.getDomain(this.recordParams);
            const domain = [];
            if (context.domain) {
                // @Sample set domain
                // domain.push(['id', '=', 1]);
                // domain.push(['id', 'in', [1,11,15]]);

                domain.push(context.domain);
            }

            // Exclude black-listed ids from the domain
            const blackListedIds = this._getSearchBlacklist();
            if (blackListedIds.length) {
                domain.push(['id', 'not in', blackListedIds]);
            }

            const nameSearch = this._rpc({
                model: this.field.relation,
                method: "name_search",
                kwargs: {
                    name: value,
                    args: domain,
                    operator: "ilike",
                    limit: this.limit + 1,
                    context,
                }
            });
            const results = await this.orderer.add(nameSearch);

            // Format results to fit the options dropdown
            let values = results.map((result) => {
                const [id, fullName] = result;
                const displayName = this._getDisplayName(fullName).trim();
                result[1] = displayName;
                return {
                    id,
                    // label: escape(displayName) || data.noDisplayContent,
                    label: displayName || data.noDisplayContent,
                    value: displayName,
                    name: displayName,
                };
            });

            // Add "Search more..." option if results count is higher than the limit
            if (this.limit <= values.length) {
            // if (this.limit < values.length) {
                values = this._manageSearchMore(values, value, domain, context);
            }
            if (!this.can_create) {
                return values;
            }

            // Additional options...
            const canQuickCreate = !this.nodeOptions.no_quick_create;
            const canCreateEdit = !this.nodeOptions.no_create_edit;
            if (value.length) {
                // "Quick create" option
                const nameExists = results.some((result) => result[1] === value);
                if (canQuickCreate && !nameExists) {
                    values.push({
                        // label: sprintf(
                        //     _t(`Create "<strong>%s</strong>"`),
                        //     escape(value)
                        // ),
                        label: sprintf(
                            'Create "<strong>%s</strong>"',
                            value
                        ),
                        action: () => this._quickCreate(value),
                        classname: 'o_m2o_dropdown_option'
                    });
                }
                // "Create and Edit" option
                if (canCreateEdit) {
                    const valueContext = this._createContext(value);
                    values.push({
                        label: "Create and Edit...",
                        action: () => {
                            // Input value is cleared and the form popup opens
                            this.el.querySelector(':scope input').value = "";
                            return this._searchCreatePopup('form', false, valueContext);
                        },
                        classname: 'o_m2o_dropdown_option',
                    });
                }
                // "No results" option
                if (!values.length) {
                    values.push({
                        label: "No results to show...",
                    });
                }
            } else if (!this.value && (canQuickCreate || canCreateEdit)) {
                // "Start typing" option
                values.push({
                    label: "Start typing...",
                    classname: 'o_m2o_start_typing',
                });
            }
            return values;
        },

        reinitialize: function () {
            this._update_field_relation();
            this._super.apply(this, arguments);
        },
    });


    field_registry.add('api_m2o', FieldApiM2O);

    return FieldApiM2O;
});
