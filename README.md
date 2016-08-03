# kubernetes-config-pinner

## Why - What is the problem we're trying to solve?

In the future we're going to be running multiple clusters
(e.g. one per warehouse, one in the hub, one in headoffice, one for dev of the cluster itself)

Deploying individual applications to each of these clusters leaves us with the problem
of coordinating deployments, making sure all the versions we deployed to cluster X work together,
deploying things in sync to cluster Y (or at least, deploying the set of versions we've already tested together)


Another issue is, can we roll back to exactly the thing we had running before?

## What can we do about this?

We can bundle up the latest version of every application we want to deploy to our "standard cluster"
Then we can test this bundle of software, and know all of the versions work together.
Then this can be deployed to our test warehouse, and burnt in for a week or whatever.
Then *exactly* the same bundle can be deployed to other environments.

The key point here is we pin/snapshot the versions of all the constituent parts, and
declare the combination a new version (say based on the timestamp of the build)
This bundle should be immutable, and whenever it's deployed it should give exactly the same result.


## How do we do this?

* This project collects a set of yaml files from a hierarchical set of repositories.
* It looks up the docker images referenced in the registry, and rewrites those references
with the current hash (thus making them immutable)
* It generates an `output` directory for use with `kubectl`

This project is used in a pipeline in Go, that feeds the generated artifact (the output directory) into a deploy job

### Repo spec
* `manifests/`: Place yaml files here
* `dependencies-v1`: Line delimited git repo names

### Local Example
`./run -vv` in this repo
* Creates a virtualenv
* Installs dependencies
* Pulls down git@gitlab.tech.lastmile.com:platform-automation/kubernetes-cluster-base.git and all it's dependencies, recursively
* Generates manifests in `./output`, ready for `kubectl apply -f output/`
```
m@hotcpc17686:~/git/kubernetes-config-pinner$ ./run -vv
INFO:__main__:Collecting git@gitlab.tech.lastmile.com:platform-automation/kubernetes-cluster-base.git...
INFO:__main__:Collecting git@gitlab.tech.lastmile.com:platform-automation/kubernetes-newrelic.git...
INFO:__main__:Collecting git@gitlab.tech.lastmile.com:platform-automation/kubernetes-chaosmonkey.git...
INFO:__main__:Collecting git@gitlab.tech.lastmile.com:platform-automation/kubernetes-selfhosting.git...
INFO:__main__:Collecting git@gitlab.tech.lastmile.com:platform-automation/kubernetes-prometheus.git...
Now run:
    kubectl apply -f output/
```

### Under the hood
* Git repos are cached in `./cache`
* Collected manifests are saved (before pinning) in `./collected`
