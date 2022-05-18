- Do not allow to create requests from emails that come from email addresses that are aliases (managed by odoo).
  This is needed to avoid possible infinite loops when two emails start sending autoreplies to each other.
- Starting from this version in *Email* field on request, only email address will be saved.
  The author name will be saved in *Author name* field.
  Previously, author name was saved in *Author name* field, but it also was
  present in *Email* field in format ```Author name <author@email.com>```.
