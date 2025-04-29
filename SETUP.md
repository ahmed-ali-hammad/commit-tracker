# 🏁 Setup
These instructions will get you a copy of the project up and running on your local machine.

### Prerequisites
 - [Docker](https://docs.docker.com/)
 - [Docker Compose](https://docs.docker.com/compose/)

### GitHub Token
First, create a GitHub token by following the instructions provided here.
[Creating a Github fine-grained personal access token](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens#creating-a-fine-grained-personal-access-token)


After generating the token, add it to the `GITHUB_ACCESS_TOKEN` variable in the `./config/.env.example` file, and then save the file.

### Installing
If you're opening this project using [devcontainers](https://containers.dev/) then your docker container should be ready to go!

Otherwise you will need to start the docker compose environment `docker compose up` and open a shell into the container `commit-tracker-dev`.

```bash
# These three commands are necessary only if you're not using devcontainers. If you're using devcontainers, you can skip them and proceed directly to the Database Migrations section.
$ docker compose up
$ docker exec -it commit-tracker-dev /bin/bash   # spawns a shell within the docker container
$ pipenv shell  # spawns a shell within the virtualenv 
```

### Database Migrations
First Load the environments variables.
```bash
$ source ./config/.env.example
```

Then Apply the migrations.
```bash
$ alembic upgrade head  # Apply database migrations 
```

### ▶️ Running the API
```bash
# Run the web server using Click.
# Make sure you are in the project's root directory where `cli.py` is located.
$ python cli.py run-webapp
```

Endpoints:
- [API Docs](http://localhost:7090/docs)
- [Healthcheck](http://localhost:7090/health)

### 🧪 Running the tests <a name = "tests"></a>
- [pytest](https://docs.pytest.org/) is used to run unit and integration tests.

```bash 
$ pytest -s .
``` 