import click
import uvicorn


def run_service():
    """
    Launches the FastAPI webapp using Uvicorn.
    """
    uvicorn.run("src.webapp.main:app", host="0.0.0.0", port=8000, reload=True)


@click.group()
def cli():
    pass


@cli.command()
def run_webapp():
    """
    Runs the web application via Uvicorn.

    Example usage:
        python cli.py run-webapp
    """
    run_service()


if __name__ == "__main__":
    cli()
