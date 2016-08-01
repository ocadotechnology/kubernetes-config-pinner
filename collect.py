#!/usr/bin/env python

import docker
import git
import logging
import os
import shutil
import sys
import yaml

LOGGER = logging.getLogger(__name__)

def collect_configs(root_repo, cache_dir='.cache', collected_dir='.collected'):

    if not os.path.isdir(cache_dir):
        os.mkdir(cache_dir)

    if os.path.isdir(collected_dir):
        shutil.rmtree(collected_dir)

    os.mkdir(collected_dir)

    repository_urls = [root_repo]

    while repository_urls:
        repo_url = repository_urls.pop(0)
        LOGGER.info("Collecting %s...", repo_url)

        dir_name = repo_url.replace('/', '-SLASH-')
        repo_dir = os.path.join(cache_dir, dir_name)
        if not os.path.isdir(repo_dir):
            os.mkdir(repo_dir)
            repo = git.Repo.init(repo_dir)
            repo.create_remote('origin', repo_url)

        repo = git.Repo(repo_dir)
        origin = repo.remotes.origin
        origin.fetch()
        origin.pull(origin.refs[0].remote_head)

        dependency_file = os.path.join(repo_dir, 'dependencies-v1')
        if os.path.isfile(dependency_file):
            with open(dependency_file) as fobj:
                for line in fobj.readlines():
                    repository_urls.append(line.strip())

        kubernetes_file = os.path.join(repo_dir, 'main.yaml')
        if os.path.isfile(kubernetes_file):
            destination_file = os.path.join(collected_dir, dir_name + '.yaml')
            shutil.copy(kubernetes_file, destination_file)


def process_configs(collected_dir='.collected', output_dir='output'):

    if os.path.isdir(output_dir):
        shutil.rmtree(output_dir)

    os.mkdir(output_dir)

    for filename in os.listdir(collected_dir):
        with open(os.path.join(collected_dir, filename)) as fobj:
            data = yaml.safe_load(fobj.read())

        replace_images(data)

        with open(os.path.join(output_dir, filename), 'w') as fobj:
            fobj.write(yaml.dump(data))


def replace_images(data):
    if isinstance(data, basestring):
        return
    if hasattr(data, 'iteritems'):
        for key, value in data.iteritems():
            if key == 'image':
                data[key] = replacement_image(value)
            replace_images(value)
    try:
        iter(data)
    except TypeError:
        pass
    else:
        for item in data:
            replace_images(item)


def replacement_image(image_name):
    docker_client = docker.Client(version='auto')
    docker_client.pull(image_name)

    image_hash = docker_client.inspect_image(image_name)['Id']
    new_image_name = "%s:%s" % (image_name.split(':')[0], image_hash)

    LOGGER.debug("Replacing image %s with %s", image_name, new_image_name)
    return new_image_name


def main(argv):
    assert(len(argv) == 2)

    root_repo = argv[1]

    #collect_configs(root_repo)
    process_configs()


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger('git').level = logging.INFO
    main(sys.argv)
