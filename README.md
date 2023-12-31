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
