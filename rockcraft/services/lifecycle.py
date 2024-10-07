# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2023 Canonical Ltd.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 3 as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""Rockcraft Lifecycle service."""

from pathlib import Path
from typing import cast

from craft_application import LifecycleService
from craft_parts.infos import ProjectInfo, StepInfo
from craft_parts import callbacks
from overrides import override  # type: ignore[reportUnknownVariableType]
from craft_cli import emit


from rockcraft import layers
from rockcraft.models.project import Project
import subprocess as sub


class RockcraftLifecycleService(LifecycleService):
    """Rockcraft-specific lifecycle service."""

    @override
    def setup(self) -> None:
        """Initialize the LifecycleManager with previously-set arguments."""
        # pylint: disable=import-outside-toplevel
        # This inner import is necessary to resolve a cyclic import
        from rockcraft.services import RockcraftServiceFactory

        # Configure extra args to the LifecycleManager
        project = cast(Project, self._project)

        services = cast(RockcraftServiceFactory, self._services)
        image_service = services.image
        image_info = image_service.obtain_image()

        self._manager_kwargs.update(
            base_layer_dir=image_info.base_layer_dir,
            base_layer_hash=image_info.base_digest,
            base=project.base,
            project_name=project.name,
            rootfs_dir=image_info.base_layer_dir,
        )

        super().setup()

    @override
    def post_prime(self, step_info: StepInfo) -> bool:
        """Perform base-layer pruning on primed files."""
        prime_dir = step_info.prime_dir
        base_layer_dir = step_info.rootfs_dir
        files: set[str]

        files = step_info.state.files if step_info.state else set()
        layers.prune_prime_files(prime_dir, files, base_layer_dir)

        _python_usrmerge_fix(step_info)

        return True

    @classmethod
    def _make_tmpfs_clone(cls, src_dir: Path, target_dir: Path):
        """Make clone of src_dir mounted on tmpfs at target_dir.

        Note: any existing files or directories at target_dir will be removed."""
        sub.run(["rm", "-rf", target_dir])  # Remove existing data, if any.

        sub.run(["mkdir", "-p", target_dir])  # Recreate the target directory and ...
        sub.run(
            ["chown", f"--reference={src_dir}", target_dir]
        )  # copy owner/group from src
        sub.run(["chmod", f"--reference={src_dir}", target_dir])  # copy mode from src

        # TODO: set max tmpfs size
        # determine minimum size in bytes required for mount. This figure will be
        # rounded up to the nearest page by tmpfs.
        # min_size = sum(path.stat().st_size for path in src_dir.rglob("*"))
        # overhead = 10**6  # 1MB. Overhead required for copying apt files in.
        # tmpfs_size = min_size + overhead # bytes
        # sub.run(
        #     [
        #         "mount",
        #         "-t",
        #         "tmpfs",
        #         "-o",
        #         f"size={tmpfs_size}",
        #         "tmpfs",
        #         target_dir,
        #     ]
        # )
        sub.run(["mount", "-t", "tmpfs", "-o", "size=50%", "tmpfs", target_dir])

        # TODO: if we copy /etc/apt in destructive mode we may end up with extra
        # config data like PPAs should we back up the original overlay /etc/apt,
        # copy it to the tmpfs, then append only the pro changes?
        sub.run(["cp", "-prT", src_dir, target_dir])

    @classmethod
    def _remove_tmpfs_clone(cls, target_dir: Path):
        """Remove tmpfs clone at target_dir"""
        sub.run(["umount", target_dir])

    @classmethod
    def _clone_build_env_apt_config(cls, rootfs_dir: Path):
        """Configure callbacks to clone the build environment's apt configuration to overlay rootfs_dir.

        The configuration cloned from /etc/apt, will be mounted in a tmpfs, and unmounted after the
        overlay has completed all actions."""
        apt_cfg_dir = Path("etc/apt")
        env_root = Path("/")

        env_apt_cfg_dir = env_root / apt_cfg_dir
        rootfs_apt_cfg_dir = rootfs_dir / apt_cfg_dir

        # register callbacks for setup and cleanup of overlay apt cfg
        def prologue_callback(project_info: ProjectInfo):
            """function for prologue callback"""
            emit.debug(
                f"Overlay prologue: Cloning {env_apt_cfg_dir} as tmpfs at {rootfs_apt_cfg_dir}"
            )
            cls._make_tmpfs_clone(env_apt_cfg_dir, rootfs_apt_cfg_dir)

        callbacks.register_prologue(prologue_callback)

        def epilogue_callback(project_info: ProjectInfo):
            """function for epilogue callback"""
            emit.debug(f"Overlay epilogue: Unmounting {rootfs_apt_cfg_dir}")
            cls._remove_tmpfs_clone(rootfs_apt_cfg_dir)

        callbacks.register_epilogue(epilogue_callback)

    # TODO: check if this step is already completed? remove if so
    @classmethod
    def _upgrade_overlay(cls, rootfs_dir: Path):
        """Configure callback to upgrade overlay before actions begin."""

        def prologue_callback(project_info: ProjectInfo):
            emit.debug(f"Upgrading overlay rootfs {rootfs_dir}")

            sub.run(["cp", "/etc/resolv.conf", f"{rootfs_dir}/etc/resolv.conf"])
            sub.run(["mount", "--bind", "/dev", f"{rootfs_dir}/dev"])
            sub.run(["chroot", rootfs_dir, "apt-get", "install", "ca-certificates"])
            sub.run(["chroot", rootfs_dir, "apt-get", "update"])
            sub.run(["chroot", rootfs_dir, "apt-get", "upgrade"])
            sub.run(["umount", f"{rootfs_dir}/dev"])

        callbacks.register_prologue(prologue_callback)

    @override
    def run(self, step_name: str | None, part_names: list[str] | None = None) -> None:
        """Run the lifecycle manager for the parts."""

        rootfs_dir = self._manager_kwargs["base_layer_dir"]

        # TODO: detect if we are using pro
        self._clone_build_env_apt_config(rootfs_dir)

        # TODO: check if this step is already completed for every overlay? remove if so
        self._upgrade_overlay(rootfs_dir)

        super().run(step_name, part_names)


def _python_usrmerge_fix(step_info: StepInfo) -> None:
    """Fix 'lib64' symlinks created by the Python plugin on ubuntu@24.04 projects."""
    if step_info.project_info.base != "ubuntu@24.04":
        # The issue only affects rocks with 24.04 bases.
        return

    state = step_info.state
    if state is None:
        # Can't inspect the files without a StepState.
        return

    if state.part_properties["plugin"] != "python":
        # Be conservative and don't try to fix the files if they didn't come
        # from the Python plugin.
        return

    if "lib64" not in state.files:
        return

    prime_dir = step_info.prime_dir
    lib64 = prime_dir / "lib64"
    if lib64.is_symlink() and lib64.readlink() == Path("lib"):
        lib64.unlink()
