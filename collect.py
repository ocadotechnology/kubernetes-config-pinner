#!/usr/bin/env python

import argparse
import docker
import git
import logging
import os
import shutil
import six
import sys
import yaml

LOGGER = logging.getLogger(__name__)

def collect_configs(repository_urls, cache_dir='.cache', collected_dir='.collected'):

    if not os.path.isdir(cache_dir):
        os.mkdir(cache_dir)

    if os.path.isdir(collected_dir):
        shutil.rmtree(collected_dir)

    os.mkdir(collected_dir)

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

        kubernetes_directory = os.path.join(repo_dir, 'manifests')
        if os.path.isdir(kubernetes_directory):
            for kubernetes_file in os.listdir(kubernetes_directory):
                destination_file = os.path.join(collected_dir, dir_name + '-' + kubernetes_file)
                shutil.copy(os.path.join(kubernetes_directory, kubernetes_file), destination_file)


def process_configs(collected_dir='.collected', output_dir='output'):

    if os.path.isdir(output_dir):
        shutil.rmtree(output_dir)

    os.mkdir(output_dir)

    for filename in os.listdir(collected_dir):
        with open(os.path.join(collected_dir, filename)) as fobj:
            data = list(yaml.safe_load_all(fobj.read()))

        replace_images(data)

        with open(os.path.join(output_dir, filename), 'w') as fobj:
            fobj.write(
                yaml.safe_dump_all(
                    data,
                    default_flow_style=False,
                ),
            )


def replace_images(data):
    if isinstance(data, six.string_types):
        return
    if hasattr(data, 'items'):
        for key, value in data.items():
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
    if image_name.startswith('gcr'):
        LOGGER.warning("Not pinning gcr '%s', due to problems with gcr/nexus mirrors", image_name)
        return image_name

    docker_client = docker.Client(version='auto')
    docker_client.pull(image_name)

    repo_digests = docker_client.inspect_image(image_name)['RepoDigests']
    if not repo_digests:
        LOGGER.warning("No RepoDigest found for %s", image_name)
        return image_name

    new_image_name = repo_digests[0]

    LOGGER.debug("Replacing image %s with %s", image_name, new_image_name)
    return new_image_name


def main(repository_urls, output_dir):
    collect_configs(repository_urls)
    process_configs(output_dir=output_dir)


def build_parser():
    parser = argparse.ArgumentParser()

    parser.add_argument('base_repo_name', nargs='+')

    parser.add_argument('--verbose', '-v', action='count', default=0)
    parser.add_argument('--output-dir', default='output')

    return parser

if __name__ == '__main__':
    parser = build_parser()
    args = parser.parse_args()

    logging.basicConfig(level=[logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG][args.verbose])
    logging.getLogger('git').level = logging.INFO
    logging.getLogger('docker').level = logging.INFO
    logging.getLogger('requests').level = logging.INFO
    main(args.base_repo_name, output_dir=args.output_dir)
