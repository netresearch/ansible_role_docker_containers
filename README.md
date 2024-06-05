# Docker Containers Ansible Role

## What does this role do?

This Ansible role provides a way to deploy multiple Docker containers.

## Requirements

- Debian 11 (bullseye) / 12 (bookworm)
- Docker on target systems
- Ansible 2.15.0

## Variables

| Name                            | Default Value | Description |
| ------------------------------- | ------------- | ----------- |
| `netresearch_docker_containers` | `[]`          | Containers  |

### Container definition

```yml
netresearch_docker_containers:
  - name: string
    image: string
    # dictionary or undefined
    login:
      registry: string
      username: string
      password: string
    # Just like the one in `community.general.docker_container`
    # You have to provide this, an empty array is fine.
    networks: []
    # Just like the one in `community.general.docker_container`
    network_mode: string
    # Just like the one in `community.general.docker_container`
    labels: {}
    # Just like the one in `community.general.docker_container`
    restart_policy: string
    # Just like the one in `community.general.docker_container`
    ports: []
    # Just like the one in `community.general.docker_container`
    env: {}
    # Just like the one in `community.general.docker_container`
    mounts: []
    # Just like the one in `community.general.docker_container`
    device_requests: []
```

### Example:

```yml
netresearch_docker_containers:
  - name: app
    image: yourapp:latest
    labels:
      - traefik.enabled=true
    networks:
      - name: "traefik-network"
    env:
      SOME_ENV_VAR: "somecontent"
    mounts:
      - type: bind
        source: /srv/app
        target: /data

  - name: traefik
    image: traefik/traefik:latest
    restart_policy: always
    ports:
      - "80:80"
      - "443:443"
    networks:
      - name: "traefik-network"

  - name: raybeam
    image: ghcr.io/netresearch/raybeam:latest
    login: # This will log into the GitHub Container Registry
      registry: "ghcr.io"
      username: "yourusername"
      password: "yourpassword"
    restart_policy: unless-stopped
    networks:
      - name: "traefik-network"
    labels:
      - traefik.enable=true
      # ...

  - name: ollama
    image: ollama/ollama
    ports:
      - "11434:11434"
    runtime: nvidia
    device_requests:
      - driver: nvidia
        count: -1
        capabilities:
          - - gpu
            - utility

  - name: nvidia-gpu-exporter
    image: utkuozdemir/nvidia_gpu_exporter:1.1.0
    ports:
      - "9835:9835"
    devices:
      - /dev/nvidiactl:/dev/nvidiactl
      - /dev/nvidia0:/dev/nvidia0
    mounts:
      - type: bind
        source: /usr/bin/nvidia-smi
        target: /usr/bin/nvidia-smi
      - type: bind
        source: /usr/lib/x86_64-linux-gnu/libnvidia-ml.so
        target: /usr/lib/x86_64-linux-gnu/libnvidia-ml.so
      - type: bind
        source: /usr/lib/x86_64-linux-gnu/libnvidia-ml.so.1
        target: /usr/lib/x86_64-linux-gnu/libnvidia-ml.so.1
```

## Testing

For simpler testing we have included molecule tests, which you can run with

```shell
molecule test
```

### Prerequisites

- `ansible`
- `molecule`
- A molecule driver depending on which scenario you want to run:
  - `default` => `molecule-docker`
  - `with-vagrant` => `molecule_vagrant`

For further information we have included the installation guide for `molecule` [here](./molecule/default/INSTALL.rst).

## License

This Ansible role is licensed under the [MIT License](./LICENSE).

## Contributing

Feel free to contribute by creating a Pull Request!

This project uses [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) for commit messages and the default `gofmt` formatting rules.
