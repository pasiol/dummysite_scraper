import os
import logging
import time
from datetime import datetime
import requests
import validators
from bs4 import BeautifulSoup
from kubernetes import client, config
from kubernetes.client.rest import ApiException

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

def get_dummy_site(dummysite):
    url = ""
    if "spec" in dummysite.keys():
        if "website_url" in dummysite["spec"].keys():
            url = dummysite["spec"]["website_url"]
            if validators.url(url):
                try:
                    page = requests.get(url)
                    soup = BeautifulSoup(page.content, "html.parser")
                    return page.text.replace("\n", ""), soup.text, url
                except Exception as error:
                    logger.critical(f"requesting the page {url} failed: {error}")
                    os.exit(1)
    return "", ""


def write_dummy_site_on_disk(html, url):
    if os.path.exists(os.getenv("WWW_ROOT")):
        subfolder = str(url).replace("https://", "")
        subfolder = subfolder.replace("http://", "")
        subfolder = subfolder.replace("/", "")  # TODO: regex
        dummysite_folder = os.path.join(os.getenv("WWW_ROOT"), subfolder)
        if not os.path.exists(dummysite_folder):
            try:
                os.mkdir(dummysite_folder)
            except Exception as e:
                logger.critical(f"creating folder {dummysite_folder} failed")
                os.exit(1)
        try:
            filename = os.path.join(dummysite_folder, "index.html")
            with open(filename, "w", encoding="utf-8") as output_file:
                output_file.writelines(html)
                update_index_page(url, subfolder)
        except Exception as e:
            logger.critical(f"writing html file failed")
            os.exit(1)


def update_index_page(url, folder):
    html = f"<p><a href=\"{os.path.join(folder, 'index.html')}\">{url}</a> - {datetime.now().isoformat(timespec='minutes')}</p>"
    index_page_file = os.path.join(os.getenv("WWW_ROOT"), "index.html")
    with open(index_page_file, "a", encoding="utf-8") as output_file:
        output_file.write(html)


def main():
    config.load_kube_config()
    #config.load_incluster_config()

    with client.ApiClient() as api_client:
        api_instance = client.CustomObjectsApi(api_client)
        # list_cluster_custom_object()
        try:
            api_response = api_instance.list_namespaced_custom_object(group="stable.dwk.stable.dwk", version="v1", namespace="default", plural="dummysites")
        except ApiException as e:
            print("Exception when calling CustomObjectsApi->create_cluster_custom_object: %s\n" % e)
        if "items" in api_response.keys():
            for item in api_response["items"]:
                if not item['spec']['succeed']:
                    if not bool(item["spec"]["succeed"]):
                        html, text, url = get_dummy_site(item)
                        logger.info(f"text version of dummysite {url}: \n{text}")
                        write_dummy_site_on_disk(html, url)
                        payload = {"spec": item["spec"]}
                        payload["spec"]["succeed"] = True
                        try:
                            api_response = api_instance.patch_namespaced_custom_object(group="stable.dwk.stable.dwk",
                                                                                       version="v1",
                                                                                       namespace="default",
                                                                                       plural="dummysites",
                                                                                       name=item['spec']['name'],
                                                                                       body=payload)
                            logger.info(f"patching dummysite object: {api_response}")
                        except ApiException as e:
                            logger.critical("patching dummysite object failed: {e}")
                            os.exit(1)
        else:
            print("no items in api")

if __name__ == "__main__":
    main()
