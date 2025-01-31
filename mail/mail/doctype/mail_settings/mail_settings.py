# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import cint
from mail.utils.cache import delete_cache
from frappe.model.document import Document
from mail.utils.validation import is_valid_host
from frappe.core.api.file import get_max_file_size


class MailSettings(Document):
	def validate(self) -> None:
		self.validate_root_domain_name()
		self.validate_spf_host()
		self.validate_postmaster()
		self.validate_default_dkim_key_size()
		self.refresh_dns_records()
		self.validate_rmq_host()
		self.validate_outgoing_max_attachment_size()
		self.validate_outgoing_total_attachments_size()

	def on_update(self) -> None:
		delete_cache("root_domain_name")
		delete_cache("postmaster")

	def validate_root_domain_name(self) -> None:
		"""Validates the Root Domain Name."""

		self.root_domain_name = self.root_domain_name.lower()

	def validate_spf_host(self) -> None:
		"""Validates the SPF Host."""

		self.spf_host = self.spf_host.lower()

		if not is_valid_host(self.spf_host):
			msg = _(
				"SPF Host {0} is invalid. It can be alphanumeric but should not contain spaces or special characters, excluding underscores.".format(
					frappe.bold(self.spf_host)
				)
			)
			frappe.throw(msg)

	def validate_postmaster(self) -> None:
		"""Validates the Postmaster."""

		if not self.postmaster:
			return

		if not frappe.db.exists("User", self.postmaster):
			frappe.throw(_("User {0} does not exist.").format(frappe.bold(self.postmaster)))
		elif not frappe.db.get_value("User", self.postmaster, "enabled"):
			frappe.throw(_("User {0} is disabled.").format(frappe.bold(self.postmaster)))
		elif not frappe.db.exists(
			"Has Role", {"parent": self.postmaster, "role": "Postmaster", "parenttype": "User"}
		):
			frappe.throw(
				_("User {0} does not have the Postmaster role.").format(
					frappe.bold(self.postmaster)
				)
			)

	def validate_default_dkim_key_size(self) -> None:
		"""Validates the DKIM Key Size."""

		if cint(self.default_dkim_key_size) < 1024:
			frappe.throw(_("DKIM Key Size must be greater than 1024."))

	def refresh_dns_records(self, save: bool = False) -> None:
		"""Generates the DNS Records."""

		records = []
		self.dns_records.clear()
		category = "Server Record"
		agent_groups = frappe.db.get_all(
			"Mail Agent Group",
			filters={"enabled": 1},
			fields=["name", "priority", "ipv4", "ipv6"],
			order_by="creation asc",
		)
		agents = frappe.db.get_all(
			"Mail Agent",
			filters={"enabled": 1},
			fields=["name", "incoming", "outgoing", "ipv4", "ipv6"],
			order_by="creation asc",
		)

		agent_group_hosts = []
		if agent_groups:
			for group in agent_groups:
				agent_group_hosts.append(group.name)

				# A Record (Agent Group)
				if group.ipv4:
					records.append(
						{
							"category": category,
							"type": "A",
							"host": group.name,
							"value": group.ipv4,
							"ttl": self.default_ttl,
						}
					)

				# AAAA Record (Agent Group)
				if group.ipv6:
					records.append(
						{
							"category": category,
							"type": "AAAA",
							"host": group.name,
							"value": group.ipv6,
							"ttl": self.default_ttl,
						}
					)

		if agents:
			outgoing_agents = []

			for agent in agents:
				if agent.outgoing:
					outgoing_agents.append(f"a:{agent.name}")

				if agent.name in agent_group_hosts:
					continue

				# A Record (Agent)
				if agent.ipv4:
					records.append(
						{
							"category": category,
							"type": "A",
							"host": agent.name,
							"value": agent.ipv4,
							"ttl": self.default_ttl,
						}
					)

				# AAAA Record (Agent)
				if agent.ipv6:
					records.append(
						{
							"category": category,
							"type": "AAAA",
							"host": agent.name,
							"value": agent.ipv6,
							"ttl": self.default_ttl,
						}
					)

			# TXT Record (Agent)
			if outgoing_agents:
				records.append(
					{
						"category": category,
						"type": "TXT",
						"host": f"{self.spf_host}.{self.root_domain_name}",
						"value": f"v=spf1 {' '.join(outgoing_agents)} ~all",
						"ttl": self.default_ttl,
					}
				)

		self.extend("dns_records", records)

		if save:
			self.save()

	def validate_rmq_host(self) -> None:
		"""Validates the rmq_host and converts it to lowercase."""

		if self.rmq_host:
			self.rmq_host = self.rmq_host.lower()

	def validate_outgoing_max_attachment_size(self) -> None:
		"""Validates the Outgoing Max Attachment Size."""

		max_file_size = cint(get_max_file_size() / 1024 / 1024)

		if self.outgoing_max_attachment_size > max_file_size:
			frappe.throw(
				_("{0} should be less than or equal to {1} MB.").format(
					frappe.bold("Max Attachment Size"), frappe.bold(max_file_size)
				)
			)

	def validate_outgoing_total_attachments_size(self) -> None:
		"""Validates the Outgoing Total Attachments Size."""

		if self.outgoing_max_attachment_size > self.outgoing_total_attachments_size:
			frappe.throw(
				_("{0} should be greater than or equal to {1}.").format(
					frappe.bold("Total Attachments Size"), frappe.bold("Max Attachment Size")
				)
			)

	@frappe.whitelist()
	def test_rabbitmq_connection(self) -> None:
		"""Tests the connection to the RabbitMQ server."""

		import socket
		from mail.rabbitmq import rabbitmq_context

		try:
			with rabbitmq_context() as rmq:
				frappe.msgprint(_("Connection Successful"), alert=True, indicator="green")
		except socket.gaierror as e:
			frappe.msgprint(e.args[1], _("Connection Failed"), indicator="red")
		except Exception as e:
			messages = []
			for error in e.args:
				if not isinstance(error, str):
					error = error.exception

				messages.append("{}: {}".format(frappe.bold(e.__class__.__name__), error))

			as_list = True
			if len(messages) == 1:
				messages = messages[0]
				as_list = False

			frappe.msgprint(messages, _("Connection Failed"), as_list=as_list, indicator="red")


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_postmaster(
	doctype: str | None = None,
	txt: str | None = None,
	searchfield: str | None = None,
	start: int = 0,
	page_len: int = 20,
	filters: dict | None = None,
) -> list:
	"""Returns the Postmaster."""

	USER = frappe.qb.DocType("User")
	HAS_ROLE = frappe.qb.DocType("Has Role")
	return (
		frappe.qb.from_(USER)
		.left_join(HAS_ROLE)
		.on(USER.name == HAS_ROLE.parent)
		.select(USER.name)
		.where(
			(USER.enabled == 1)
			& (USER.name.like(f"%{txt}%"))
			& (HAS_ROLE.role == "Postmaster")
			& (HAS_ROLE.parenttype == "User")
		)
	).run(as_dict=False)


def validate_mail_settings() -> None:
	"""Validates the mandatory fields in the Mail Settings."""

	mail_settings = frappe.get_doc("Mail Settings")
	mandatory_fields = [
		"root_domain_name",
		"spf_host",
		"default_dkim_key_size",
		"default_ttl",
	]

	for field in mandatory_fields:
		if not mail_settings.get(field):
			field_label = frappe.get_meta("Mail Settings").get_label(field)
			frappe.throw(
				_("Please set the {0} in the Mail Settings.".format(frappe.bold(field_label)))
			)
