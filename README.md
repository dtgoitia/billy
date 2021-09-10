## Set up

* Install:

  ```shell
  git clone git@github.com:dtgoitia/billy.git
  cd billy/

  # Create and activate Python virtual environment
  python3 -m venv .venv
  . .venv/bin/activate

  # install repo dependencies locally
  make install
  ```

* Configuration (mandatory):

  At `~/.config/billy/config.jsonc`:

  ```json
  {
    "projects": [
      { "id": 123, "alias": "my super project" },
      { "id": 456, "alias": "another project" }
    ]
  }
  ```

* Credentials (mandatory):

  At `~/.config/billy/credentials.jsonc`:

  ```jsonc
  {
    // Get API token at https://track.toggl.com/profile
    "gsheet_url": "https://url.to/my/google/spreadsheet",
    "toggle_api_token": "_____INSERT_API_TOKEN_HERE_____"
  }
  ```

  Follow [this instructions][1] to obtain Google Spreadsheet credentials and enable required GCP APIs.

<!-- External references -->

[1]: https://docs.gspread.org/en/latest/oauth2.html#for-end-users-using-oauth-client-id "How to obtain Google Spreadsheet credentials"
