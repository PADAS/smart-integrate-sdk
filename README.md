# SMART Integrate Connector Library

Base library for building data source extractors.

### CHANGELOG

- [1.0.7](https://github.com/PADAS/smart-integrate-sdk/releases/tag/v1.0.7): New action/configuration approach. 

  Related branch: [integrations-core-redesign](https://github.com/PADAS/smart-integrate-sdk/tree/integrations-core-redesign)

  FURTHER READING: [Software Requirement Specification](https://docs.google.com/document/d/1oCKqW6ryU662V-AIRy_AdwhjLGpWnBj_/edit?pli=1#)

## Building process

### Pre requisites

* Python 3.7+

* [Poetry](https://python-poetry.org/) (recommended). 
  Install Poetry to get started (Homebrew).

### Initialize your Environment

Since you've already installed poetry, you can use it to initialize the development environment for this project.

```shell
poetry install
```

Run a shell using poetry.

```shell
poetry shell
```

### Building a Wheel

```shell
poetry build
```

Then find a tar ball and wheel in `./dist`

