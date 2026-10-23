# Runs community.docker.docker_container and masks env values in everything it
# returns: the --diff, the container dump of -v and the module invocation of -vvv.
#
# Extra arguments (removed before the module runs):
#   redact_env   true (default): mask every env value; false: mask nothing
#   env_visible  list of env names that stay readable although redact_env is true
#
# Two layers, so a change in the module's result layout cannot silently leak:
#   - by name, in every env context of the result (env/Env keys, NAME=value lists and
#     mappings), marking changed values as "(changed)" because both sides look the same
#   - by value, in the error text keys, for values of 8+ characters
from __future__ import annotations

from ansible.errors import AnsibleActionFail
from ansible.module_utils.parsing.convert_bool import boolean
from ansible.plugins.action import ActionBase

try:
    # Core-private helper that applies module_defaults to the wrapped module,
    # the same one ansible.builtin.package/service use. Optional, see run().
    from ansible.executor.module_common import _apply_action_arg_defaults
except ImportError:  # pragma: no cover
    _apply_action_arg_defaults = None

MODULE = "community.docker.docker_container"
MASK = "********"
MIN_SCRUB = 8
ENV_KEYS = ("env", "environment")
LABEL_KEYS = ("labels",)  # may hold a key named env
TEXT_KEYS = ("msg", "stderr", "stdout", "module_stderr", "module_stdout", "exception")


def _mask(value, hit, in_env=False):
    """Mask hit env names below env keys: in NAME=value list entries and mappings."""
    if isinstance(value, dict):
        masked = {}
        for key, item in value.items():
            name = str(key)
            if in_env and not isinstance(item, (dict, list)):
                masked[key] = MASK if hit(name) else item
            elif name.lower() in LABEL_KEYS:
                masked[key] = item
            else:
                masked[key] = _mask(item, hit, in_env or name.lower() in ENV_KEYS)
        return masked
    if isinstance(value, list):
        return [_mask(v, hit, in_env) for v in value]
    if in_env and isinstance(value, str) and "=" in value:
        name = value.partition("=")[0]
        if hit(name):
            return f"{name}={MASK}"
    return value


def _scrub(value, secrets):
    """Replace the secret values in strings, longest first."""
    if isinstance(value, dict):
        return {k: _scrub(v, secrets) for k, v in value.items()}
    if isinstance(value, list):
        return [_scrub(v, secrets) for v in value]
    if isinstance(value, str):
        for secret in secrets:
            value = value.replace(secret, MASK)
    return value


def _env_pairs(entries):
    return dict(e.split("=", 1) for e in entries or [] if isinstance(e, str) and "=" in e)


class ActionModule(ActionBase):
    def run(self, tmp=None, task_vars=None):
        result = super().run(tmp, task_vars)
        args = dict(self._task.args)
        setting = args.pop("redact_env", None)
        try:
            # an empty value means the default, which is masking
            enabled = True if setting in (None, "") else boolean(setting)
        except TypeError:
            # boolean() would quote the offending value
            raise AnsibleActionFail("redact_env must be a boolean") from None
        visible = args.pop("env_visible", None) or []
        if isinstance(visible, str):
            visible = [v.strip() for v in visible.split(",") if v.strip()]
        visible = set(visible)

        if self._task.module_defaults:
            if _apply_action_arg_defaults is None:
                raise AnsibleActionFail(
                    "module_defaults are set but this ansible-core has no helper to apply them to "
                    "netresearch_docker_container; refusing to run the module without them"
                )
            args = _apply_action_arg_defaults(MODULE, self._task, args, self._templar)

        env = args.get("env") or {}
        if not isinstance(env, dict):
            raise AnsibleActionFail("env must be a mapping of names to values")
        unknown = sorted(visible - set(env))
        if unknown and args.get("state") != "absent":
            raise AnsibleActionFail(f"env_visible names keys that are not in env: {', '.join(unknown)}")

        def hit(name):
            return enabled and name not in visible

        result.update(self._execute_module(module_name=MODULE, module_args=args, task_vars=task_vars))
        if not enabled:
            return result

        diff = result.get("diff") if isinstance(result.get("diff"), dict) else {}
        before = _env_pairs((diff.get("before") or {}).get("env"))
        after = _env_pairs((diff.get("after") or {}).get("env"))
        changed = {k for k in after if hit(k) and before.get(k) != after[k]}

        # Values to scrub from error text: the task's masked env values, old and new.
        secrets = {str(v) for k, v in env.items() if hit(str(k))}
        secrets |= {v for k, v in before.items() if k in env and hit(k)}
        secrets = sorted((s for s in secrets if len(s) >= MIN_SCRUB), key=len, reverse=True)

        result = _mask(result, hit)
        if not isinstance(result.get("exception"), str):
            # core 2.19+ prints this error summary object, it holds the raw module message
            result.pop("exception", None)
        for key in TEXT_KEYS:
            if secrets and key in result:
                result[key] = _scrub(result[key], secrets)
        marked = (result.get("diff") or {}).get("after") if isinstance(result.get("diff"), dict) else None
        if changed and isinstance(marked, dict) and isinstance(marked.get("env"), list):
            marked["env"] = [
                f"{e} (changed)" if isinstance(e, str) and e.split("=", 1)[0] in changed else e for e in marked["env"]
            ]
        return result
