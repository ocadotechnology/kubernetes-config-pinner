FROM python:3.5-onbuild

ENTRYPOINT ["/usr/src/app/collect.py"]
