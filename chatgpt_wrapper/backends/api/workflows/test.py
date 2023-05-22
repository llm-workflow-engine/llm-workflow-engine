from prefect import flow, task

from chatgpt_wrapper.core.workflow import Workflow

from typing import List
import httpx

@task(retries=3)
def get_stars(repo: str):
    url = f"https://api.github.com/repos/{repo}"
    count = httpx.get(url).json()["stargazers_count"]
    return f"{repo} has {count} stars!"

@flow(name="GitHub Stars")
def github_stars(repos: List[str]):
    counts = []
    for repo in repos:
        counts.append(get_stars(repo))
    return counts

class Test(Workflow):

    def default_config(self):
        return {
        }

    def setup(self):
        self.log.debug("Setting up test workflow")

    def run(self, *args):
        try:
            self.log.debug("Running test workflow")
            counts = github_stars(["PrefectHQ/Prefect"])
            self.log.debug(f"Ran test workflow, got {counts}")
        except Exception as e:
            return False, None, f"Error getting stars: {e}"
        return True, counts, ", ".join(counts)
