import click
import uvicorn


def run_service():
    uvicorn.run("src.webapp.main:app", host="0.0.0.0", port=8000, reload=True)


@click.group()
def cli():
    pass


@cli.command()
def run_webapp():
    run_service()


if __name__ == "__main__":
    cli()
