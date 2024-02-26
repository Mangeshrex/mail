// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Mailbox", {
	setup(frm) {
        frm.set_query("user", function(doc) {
			return {
				query: "mail.mail.doctype.mailbox.mailbox.get_user",
				filters: {
					"domain_name": doc.domain_name || " "
				}
			};
		});
	},
});