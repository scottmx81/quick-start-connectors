# Microsoft 365

This package is a utility for connecting Cohere to Microsoft 365. It features a simple local development setup.

It uses Microsoft Graph API run the search query and return matching results.

## Configuration

1. Register a new Microsoft App

Running this connector requires access to Microsoft 365. For development purposes,
you can register for the Microsoft 365 developer program, which will grant temporary
access to a Microsoft 365.

For the connector to work, you must create a new application. To do this, go to the
Microsoft Entra admin center:

https://entra.microsoft.com/

Navigate to Applications > App registrations > New registration option.

Select "Web" as the platform, and add a redirect URI as needed. For App auth, you can set the URI to the server you're hosting the connector on. For Delegated auth, set the URI to `https://api.cohere.com/v1/connectors/oauth/token`.

Next, we will configure your App permissions (this requires Admin access on Entra). Head under your app's API permissions page and select Add a permission > Microsoft Graph. From here, select either Application of Delegated permissions as required, and check the following permissions:

- `offline_access` (only if using Delegated)
- `Application.Read.All`
- `Files.ReadWrite.All` (MSFT requires this to enable search, though this connector will never write anything)

Go back to API permissions, and as an Admin, select Grant admin consent for MSFT.

Then, head to Certificates & Secrets and create a new client secret.

The above environment variables can be read from a .env file. See `.env-template` for an example `.env` file.

2. Authentication

We will now cover the two types of authentication supported by this connector. To use either type of authentication, specify the `MSGRAPH_AUTH_TYPE` environment variable as either `application` for App auth, or `user` for Delegated auth.

### Application authentication

For application authentication, you will need to setup the following environment variables in a `.env` file:

```bash
MSGRAPH_AUTH_TYPE=application
MSGRAPH_CLIENT_ID=<obtainable from app details>
MSGRAPH_CLIENT_SECRET=<obtainable from app credentials>
MSGRAPH_TENANT_ID=<obtainable from app details>
```

### Delegated authentication

For delegated authentication, you will need to add the following environment variable in a `.env` file:

```bash
MSGRAPH_AUTH_TYPE=user
```

Other than that, no configuration is needed. When registering the connector you will specify all the details required for Cohere to handle the authentication steps (details to follow).

To configure delegated user OAuth, make sure the app you registered in Step 1 has a Redirect URI to `https://api.cohere.com/v1/connectors/oauth/token`.

Next, register the connector with Cohere's API using the following configuration.

```bash
 curl  -X POST \
   'https://api.cohere.ai/v1/connectors' \
   --header 'Accept: */*' \
   --header 'Authorization: Bearer {COHERE-API-KEY}' \
   --header 'Content-Type: application/json' \
   --data-raw '{
   "name": "MS Graph with OAuth",
   "url": "{YOUR_CONNECTOR-URL}",
   "oauth": {
     "client_id": "{Your Microsoft App CLIENT-ID}",
     "client_secret": "{Your Microsoft App CLIENT-SECRET}",
     "authorize_url": "https://login.microsoftonline.com/{Your Microsoft App TENANT-ID}/oauth2/v2.0/authorize",
     "token_url": "https://login.microsoftonline.com/{Your Microsoft App TENANT-ID}/oauth2/v2.0/token",
     "scope": ".default offline_access"
   }
 }'
```

Once properly registered, whenever a search request is made Cohere will take care of authorizing the current user and passing the correct access tokens in the request headers.

### Provision Unstructured

Processing the files found on OneDrive requires the Unstructured API. The Unstructured API is
a commercially backed, Open Source project. It is available as a hosted API, Docker image, and as a
Python package, which can be manually set up.

To configure Unstructured, setup these two environment variables:

```bash
MSGRAPH_UNSTRUCTURED_BASE_URL=https://api.unstructured.io
MSGRAPH_UNSTRUCTURED_API_KEY=(optional)
```

By default, this connector uses the hosted `https://api.unstructured.io` API that requires an API key obtainable by registering an account [here](https://unstructured.io/api-key).

Alternatively, you can use the API by hosting it yourself with their provided Docker image. If you've used Docker before, the setup is relatively straightforward. Please follow the instructions for setting up the Docker image in the Unstructured [documentation](https://unstructured-io.github.io/unstructured/api.html#using-docker-images). With this self-hosted option, no API key is required.

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
take the credentials (:code:`MSGRAPH_TENANT_ID`, :code:`MSGRAPH_CLIENT_ID` and :code:`MSGRAPH_CLIENT_SECRET`)
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
