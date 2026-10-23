# Docker Containers Ansible Role

## What does this role do?

This Ansible role provides a way to deploy multiple Docker containers.

## Requirements

- Debian 11 (bullseye) / 12 (bookworm)
- Docker on target systems
- ansible-core 2.19 or newer

## Variables

| Name                                 | Default Value | Description |
| ------------------------------------ | ------------- | ----------- |
| `netresearch_docker_containers`      | `[]`          | Containers  |
| `netresearch_docker_containers_only` | `[]`          | Limit a run to these container names. Empty manages all. Accepts a list or a comma-separated string. |
| `netresearch_docker_containers_redact_env` | `true` | Mask every container env value in task output. A container can override it with `redact_env`. |

### Env values in task output

`community.docker.docker_container` prints every `NAME=value` env entry of a
recreated container in its `--diff`, the full container config with `-v` and
the module arguments with `-vvv`. The role therefore runs the module through
its own action plugin, which masks **all** env values in that output by
default. The rest of the diff (image, labels, ports, mounts) stays readable,
error messages stay readable apart from the masked values, and the containers
are not changed in any way.

Per container, `env_visible` lists the env names that stay readable, and
`redact_env: false` switches masking off for the whole container. The role-wide
default is `netresearch_docker_containers_redact_env`.

```yml
netresearch_docker_containers:
  - name: app
    image: example/app
    env:
      DB_PASSWORD: "{{ lookup('community.hashi_vault.hashi_vault', '...') }}"  # masked
      LOG_LEVEL: info                                                           # readable
    env_visible: [LOG_LEVEL]
```

A changed value shows up as `DB_PASSWORD=******** (changed)` on the new side of
the diff, so a rotation is still visible. A name in `env_visible` that is not in
`env` fails the run (it names the key, never a value).

Limits to know:

- Masking covers the output only. The values are still part of the container
  configuration on the host (`docker inspect`).
- Everything under an env key is masked, including the variables the image
  defines itself (such as `PATH`). Other output (command, labels, mounts) is
  left as it is, so a secret placed there is not masked.
- Masked values of 8 or more characters are also removed from error messages.
  Shorter values, and values that only come from an `env_file`, are masked by
  name only.
- The `netresearch_docker_container` action only exists inside the role, do not
  call it from your own tasks.
- If `module_defaults` are set for the play, the plugin applies them to the
  wrapped module through an ansible-core helper. When that helper does not exist
  in the installed ansible-core, the run fails instead of ignoring the defaults.

### Limiting a run to specific containers

By default the role reconciles **every** container in
`netresearch_docker_containers`. To act on only a subset (for example to deploy
a single container without re-pulling/recreating the others on a shared host),
set `netresearch_docker_containers_only`. It accepts a list or a
comma-separated string and only manages the networks of the selected
containers. An unknown name fails the run early.

```shell
# single container
ansible-playbook site.yml --limit myhost --tags docker-containers \
  -e 'netresearch_docker_containers_only=dns'

# a group of containers
ansible-playbook site.yml --limit myhost --tags docker-containers \
  -e '{"netresearch_docker_containers_only": ["dns", "composer"]}'
```

The role selects and iterates by container **name** (names must be unique -
duplicates fail the run) and resolves each entry's full definition only in
that container's own iteration. On ansible-core >= 2.19 (the role's minimum,
where templating is lazy per value) this means a broken Jinja value in an
entry **not selected for the run** - say a secret lookup against an
unreachable backend - can never block the selected containers (#31). Three
limits:

- `name` must be a **plain string** (a templated name defeats the name-first
  selection);
- among the CO-selected entries ordinary fail-fast still applies, and their
  `networks` values are all resolved before the first container starts;
- on ansible-core **< 2.19** the engine templates the whole list on any
  access, so the isolation cannot hold there: keep unresolvable lookups out of
  the shared list entirely on old cores.

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
    # Just like the one in `community.docker.docker_container`
    # You have to provide this, an empty array is fine.
    networks: []
    # Just like the one in `community.docker.docker_container`
    network_mode: string
    # Just like the one in `community.docker.docker_container`
    labels: {}
    # Just like the one in `community.docker.docker_container`
    restart_policy: string
    # Just like the one in `community.docker.docker_container`
    ports: []
    # Just like the one in `community.docker.docker_container`
    env: {}
    # `false` shows this container's env values in task output (see above)
    redact_env: true
    # Env names that stay readable in task output although masking is on
    env_visible: []
    # Just like the one in `community.docker.docker_container`
    mounts: []
    # Just like the one in `community.docker.docker_container`
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

For simpler testing we have included molecule tests. They need a local Docker
daemon and [uv](https://docs.astral.sh/uv/); nothing is installed into your
Python environment:

```shell
# one scenario, with the ansible-core you want to test against
uvx --from molecule --with 'molecule-plugins[docker]' --with 'ansible-core==2.20.*' \
  molecule test -s env-redact
```

Run `molecule test` without `-s` for the `default` scenario. Scenarios:

| Scenario | What it guards |
| -------- | -------------- |
| `default` | The role end to end, including the `state: absent` tombstone entry. |
| `only-filter-isolation` | `netresearch_docker_containers_only` never templates unselected entries. |
| `no-log-leak` | A registry password never reaches the play output. |
| `env-redact` | Env values never reach the play output (`--diff`, `-v`, `-vvv`) unless allowed, and the containers still run with the real values. |
| `with-vagrant` | The role on a Vagrant VM (needs `molecule-vagrant`, not run in CI). |

The leak guards (`no-log-leak`, `env-redact`) only turn red in CI, which greps
the output for their canary string; the run itself passes either way. Check it yourself with
the same `uvx` command with `2>&1 | grep -F CANARY_ENV_must_not_appear`, which must print nothing.

## License

This Ansible role is licensed under the [MIT License](./LICENSE).

## Contributing

Feel free to contribute by creating a Pull Request!

This project uses [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) for commit messages and the default `gofmt` formatting rules.
