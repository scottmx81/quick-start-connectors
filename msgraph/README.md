# Microsoft 365

This package is a utility for connecting Cohere to Microsoft 365.

It uses Microsoft Graph API run the search query and return matching messages.

## Configuration

To use this search provider, you must have access to Microsoft 365, with API
credentials configured. This search provider requests default permissions with scope
`https://graph.microsoft.com/.default offline_access`. This requires the permissions for the
client credential to be configured in Azure AD. It is important that the following
permissions must be allowed for MS Graph API:

* `Mail.Read`
* `offline_access`

The app registration for the provider in Microsoft Entra admin center requires
permissions to read mail messages.

This search provider requires the following environment variables to be set:

* `MSGRAPH_GRAPH_TENANT_ID`
* `MSGRAPH_GRAPH_CLIENT_ID`
* `MSGRAPH_GRAPH_CLIENT_SECRET`
* `MSGRAPH_CREDENTIAL`

These can be read from a .env file. See `.env-template`.

The values for `MSGRAPH_TENANT_ID`, `MSGRAPH_CLIENT_ID` and `MSGRAPH_CLIENT_SECRET` come from
Microsoft 365 admin. The value for `MSGRAPH_CREDENTIAL` contains a base64 encoded access token
and refresh token values. To obtain the value for `MSGRAPH_CREDENTIAL`, you must go to the
URL http://localhost:5000/authorize in your browser, and grant the application permission. The
http://localhost:5000/autorize page will redirect to Microsoft 365. After granting permission
on the Microsoft site, you will be redirected back to a page in the Flask app, which will display
the value for the credential. You must copy the value in your browser, and paste it into the `.env`
file (or set as a regular environment variable), before this provider will work.

For this to work, you will need to configure the redirect URL in Microsoft 365 Admin. The value
passed by this search provider in the OAuth2 URL must match an allowed redirect URL configured
in the Microsoft 365 Admin page. For local development, redirect URL is `http://localhost:5000/token`.
For production use, the redirect URL must be configured with the appropriate hostname, by setting
the `OUTLOOK_REDIRECT_URI` environment variable.

After the client has been created, you will need to grant admin consent to the client. One
way to do this is by going to the following URL:

https://login.microsoftonline.com/{site_id}/adminconsent?client_id={client_id}&redirect_uri=http://localhost/

You must replace `{site_id}` and `{client_id}` with the appropriate values. The `redirect_uri`
must match the value that was configured when creating the client in Microsoft Entra.

It is important to note that this search provider requires delegated access to MS Graph API, that is
associated with a specific user account. This will be the user that is logged into Microsoft 365
when http://localhost:5000/authorize is opened in the browser. A consequence of requiring delegated
access is that the access token is only valid for approximately 1.5 hours. It is not possible to use
an indefinite access token or client / secret, and this provider needs to use refresh tokens.

If it is not working, you may need to go to http://localhost:5000/authorize, and copy the credential
into `.env` again.

## Development

Running this provider requires access to Microsoft 365. For development purposes,
you can register for the Microsoft 365 developer program, which will grant temporary
access to a Microsoft 365.

For the provider to work, you must register the application. To do this, go to
Microsoft Entra admin center:

https://entra.microsoft.com/

Navigate to "Applications -> App registrations", and use the "New registration" option.

Select "Web" as the platform, and ensure you add a redirect URL, even if it is optional.
The redirect URL is required for the admin consent step to work. This provider does not
have a redirect page implemented, but you can use http://localhost/ as the redirect URL.

On the app registration page for the app you have created, go to API permissions, and
grant permissions. For development purposes, you can grant:

* `Mail.Read`
* `offline_access`

This will get you up and running, although it is likely excessive and not recommended
for production environment. For production permission configuration, please refer to
your systems administrator for guidance.

Once you have Microsoft 365 configured with an app registration for this search provider,
take the credentials (:code:`GRAPH_TENANT_ID`, :code:`GRAPH_CLIENT_ID` and :code:`GRAPH_CLIENT_SECRET`)
and put them into a :code:`.env` file or set them as environment variables in your preferred way.

Create a virtual environment and install dependencies with poetry. We recommend using in-project virtual environments:

```bash
  poetry config virtualenvs.in-project true
  poetry install --no-root
```

To run the Flask server in development mode, please run:

```bash
  poetry run flask --app provider --debug run
```

The Flask API will be bound to :code:`localhost:5000`.

```bash
  curl --request POST \
    --url http://localhost:3000/search \
    --header 'Content-Type: application/json' \
    --data '{
    "query": "Weber charcoal"
  }'
```

Alternatively, load up the Swagger UI and try out the API from a browser: http://localhost:5000/ui/
