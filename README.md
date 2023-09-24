# A simple Jellyfin prometheus exporter in Python

This project aims at providing a [Prometheus](https://prometheus.io/) exporter for the [Jellyfin](https://jellyfin.org/) streaming server.

### Configuration

You can use environment variables when starting the container:

| Variable         | Value                                                              |
| ---------------- | ------------------------------------------------------------------ |
| `JELLYFIN_URL`   | the URL to the Jellyfin instance (default `http://localhost:8096`) |
| `JELLYFIN_TOKEN` | Jellyfin API token                                                 |

The exporter is listenning on port 8000.
