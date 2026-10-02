# Development rules

- **Always use the test database for testing. Never modify the production
  database (`reports_db`).**
  - Run the backend test suite via `python manage.py test` (it uses its own
    `test_reports_db` automatically).
  - Do NOT run `DELETE`/update/seed scripts against `reports_db`.
  - For live end-to-end checks, either run against the test database or
    create/clean up data through the application's own API and report back to
    the user before removing anything.
- Do not delete or overwrite data that may have been created by the user.