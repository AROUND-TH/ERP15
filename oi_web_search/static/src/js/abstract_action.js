odoo.define('oi_web_search.AbstractAction', function (require) {
	"use strict";

	const AbstractAction = require("web.AbstractAction");
	const MyControlPanel = require("oi_web_search.ControlPanel");

	
	AbstractAction.include({
		config: _.extend({}, AbstractAction.prototype.config, {
			ControlPanel: MyControlPanel,
		})
	});
		
	return AbstractAction;
});