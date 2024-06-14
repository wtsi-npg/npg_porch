# Development Dockerfile

The Dockerfile and scripts in this directory may be use to create a development image
that hosts both the PostgreSQL database and the npg_porch server.

The application is populated with a hard-coded administrator user, password and
administration token and is configured log to STDERR and STDOUT.

To create an image using the Dockerfile, run the following command from the root of the
repository:

```bash
docker build --rm -f docker/Dockerfile.dev -t npg_porch_dev .
```

The Dockerfile supports a number of arguments that can be passed to the `docker build`
command to configure most aspects of the application, including user names, passwords,
database names and ports. However, the default values should be suitable for most
needs.
