#!/usr/bin/env python3
# script to validate .gitlab-ci.yml

import sys
import os
import logging

import click
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning

from gitlab_lint.__init__ import __version__

DEFAULT_DOMAIN = "gitlab.com"


def validate_domain(ctx, param, value):
    from fqdn import FQDN

    domain = FQDN(value)
    if not domain.is_valid:
        raise click.BadParameter(f"{value} does not conform to RFC1035")
    return value


@click.command(context_settings={"auto_envvar_prefix": "GLL"})
@click.version_option(__version__)
# Ergonomically defaulting to GitLab.com is nice, but it can result in credential leakage
@click.option(
    "--domain",
    "-d",
    default=DEFAULT_DOMAIN,
    help="Gitlab FQDN, no protocol or trailing slash",
    callback=validate_domain,
)
@click.option("--project", "-p", help="Gitlab project ID")
@click.option("--token", "-t", help="Gitlab personal access token")
@click.option(
    "--file",
    "-f",
    default=".gitlab-ci.yml",
    help="Path to .gitlab-ci.yml, starts in local directory",
    type=click.Path(exists=True, readable=True, file_okay=True),
)
@click.option(
    "--insecure",
    "-i",
    default=False,
    is_flag=True,
    help="Suppresses TLS validity failures",
)
@click.option(
    "--reference",
    "-r",
    help="Git reference to use for validation context",
)
@click.option(
    "--verbose",
    "-v",
    default=False,
    is_flag=True,
    help="Enable verbose logging, useful for debugging and CI systems",
)
def gll(**kwargs):
    logger = logging.getLogger(__name__)
    if kwargs.get("verbose"):
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

        # Override stack trace prints if we're not verbose
        def on_crash(exctype, value, traceback):
            logger.error("Oops. Something went wrong.")

        sys.excepthook = on_crash

    # Yoink the argument we no longer need
    kwargs.pop("verbose")

    logger.debug("Received from Click: %s", kwargs)

    # GITLAB_PRIVATE_TOKEN isn't an official convention I don't think, perhaps remove it?
    # CI_JOB_TOKEN sadly doesn't have permissions to use the API we need
    argument_mapping = {
        "token": "GITLAB_PRIVATE_TOKEN",
        "reference": "CI_COMMIT_REF_NAME",
        "project": "CI_PROJECT_ID",
        "file": "CI_CONFIG_PATH",
    }
    # If not provided an argument but we can pull it from the Gitlab CI environment, do so
    for argument_name, environment_variable_name in argument_mapping.items():
        if not kwargs.get(argument_name) and os.environ.get(environment_variable_name):
            logger.debug(
                "Set %s from environment to %s",
                argument_name,
                environment_variable_name,
            )
            # Can't use setDefault because the key might be there with None
            kwargs[argument_name] = os.environ.get(environment_variable_name)

    # Special handling for domain as it defaults to a truthy value thanks to being populated by default
    #   so can't be dealt with by argument_mapping
    if kwargs.get("domain") == DEFAULT_DOMAIN and os.environ.get("CI_SERVER_HOST"):
        logger.debug(
            "Set domain from environment to %s", os.environ.get("CI_SERVER_HOST")
        )
        kwargs["domain"] = os.environ.get("CI_SERVER_HOST")

    # Destructure the dictionary to pass it in
    # I would like to convert get_validation_data to be decoupled from the arguments too, eventually
    data = get_validation_data(**kwargs)
    terminate_program(resolve_exit_code(data))


def get_validation_data(file, domain, project, token, insecure, reference):
    logger = logging.getLogger(__name__)
    """
    Creates a post to gitlab ci/lint api endpoint
    Reference: https://docs.gitlab.com/ee/api/lint.html
    """
    if insecure:
        logger.debug("Suppressing InsecureRequestWarning in urllib3")
        # Suppress error message for not securing https if insecure is False
        requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

    params = {}
    if token:
        logger.debug("Setting header 'private_token' to %s", token)
        params.update({"private_token": token})
    if reference:
        logger.debug("Setting header 'ref' to %s", reference)
        params.update({"ref": reference})
        logger.debug("Setting header 'dry_run' 'true'")
        params.update({"dry_run": "true"})  # Must be set or ref is ignored
    project_id = f"projects/{project}/" if project else ""
    logger.debug("Project string set to %s", project_id)

    with open(file, "r") as ci_file:
        response = requests.post(
            f"https://{domain}/api/v4/{project_id}ci/lint",
            json={"content": ci_file.read()},
            params=params,
            verify=not insecure,
        )
        logger.debug(response)
    if response.status_code != 200:
        raise click.ClickException(
            (
                f"API endpoint returned invalid response: \n {response.text} \n"
                "confirm your `domain`, `project`, and `token` have been set correctly"
            )
        )
    data = response.json()
    return data


def resolve_exit_code(data):
    """
    Parses response data and generates exit message and code
    :param data: json gitlab API ci/lint response data
    """
    logger = logging.getLogger(__name__)
    valid = None

    # for calling the lint api
    if "status" in data:
        valid = data["status"] == "valid"

    # for calling the lint api in the project context
    if "valid" in data:
        valid = data["valid"]

    if not valid:
        logger.info("GitLab CI configuration is invalid")
        for e in data["errors"]:
            logger.error(e)
        return 1
    else:
        logger.info("GitLab CI configuration is valid")
        return 0


def terminate_program(return_code):
    sys.exit(return_code)


if __name__ in ("__main__"):
    gll()
