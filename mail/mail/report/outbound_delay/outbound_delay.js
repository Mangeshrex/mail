// Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["Outbound Delay"] = {
	"filters": [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
			reqd: 1,
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1,
		},
		{
			fieldname: "name",
			label: __("Outgoing Mail"),
			fieldtype: "Link",
			options: "Outgoing Mail",
			get_query: () => {
				return {
					filters: {
						docstatus: 1,
						status: ["not in", ["Pending", "Transferring"]]
					},
				};
			},
		},
		{
			fieldname: "status",
			label: __("Status"),
			fieldtype: "Select",
			options: ["", "Deferred", "Deferred Bounced", "Bounced", "Sent"],
		},
		{
			fieldname: "agent",
			label: __("Agent"),
			fieldtype: frappe.user.has_role("System Manager") ? "Link" : "Data",
			options: "Mail Agent",
		},
		{
			fieldname: "domain_name",
			label: __("Domain Name"),
			fieldtype: "Link",
			options: "Mail Domain",
		},
		{
			fieldname: "from_ip",
			label: __("From IP"),
			fieldtype: "Data",
		},
		{
			fieldname: "sender",
			label: __("Sender"),
			fieldtype: "Link",
			options: "Mailbox",
		},
		{
			fieldname: "recipient",
			label: __("Recipient"),
			fieldtype: "Data",
			options: "Email",
		},
		{
			fieldname: "message_id",
			label: __("Message ID"),
			fieldtype: "Data",
		},
	]
};