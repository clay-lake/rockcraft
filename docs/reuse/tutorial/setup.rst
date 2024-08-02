

Setup
=====

For convenience we will use a fresh Ubuntu 22.04 virtual machine in this
tutorial. This can be quickly configured with `Multipass <multipass-landing_>`_.
If you have already create a virtual machine from a previous Rockcraft tutorial
feel free to skip this section.

|

Multipass Configuration
~~~~~~~~~~~~~~~~~~~~~~~

If you do not have Multipass installed on your system, please visit the
`installation instructions <install-multipass_>`_.

Once Multipass is installed, a new Ubuntu virtual machine can be created with
``multipass launch``. The command below will create a new virtual machine named
``rock-dev`` with a 10 gigabyte virtual disk containing Ubuntu 22.04.

.. code-block:: bash
   
    multipass launch --disk 10G --name rock-dev 22.04
|

Optionally, if you would like to use your own IDE in this tutorial, it is
recommended to mount your filesystem in the virtual machine. Files from your
home directory will be available in the ``~/host`` of ``rock-dev``.

.. code-block:: bash

    multipass mount $HOME rock-dev:host 
.. TODO: Add Note for windows systems here.... https://multipass.run/docs/mount-command
|

Now we can enter our new ``rock-dev`` virtual machine with ``multipass shell``.

.. code-block:: bash

    multipass shell rock-dev

.. important:: 
    Your prompt should begin with ``ubuntu@rock-dev:`` indicating you are inside the
    ``rock-dev`` virtual machine. For the remainder of this tutorial, commands
    should be executed within ``rock-dev``. To access additional shells in this
    virtual machine simply execute ``multipass shell rock-dev`` on your host
    terminal.
|

Toolchain Installation
~~~~~~~~~~~~~~~~~~~~~~

In order to create the rock, you'll need to install Rockcraft:

.. literalinclude:: /reuse/tutorial/code/task.yaml
    :language: bash
    :start-after: [docs:install-rockcraft]
    :end-before: [docs:install-rockcraft-end]
    :dedent: 2

`LXD` a package Rockcraft depends on, must be initialized prior to use. This can
be achieved by running:

.. code-block:: bash

   lxd init --auto

Finally, we will use Docker to run the rock. You can install it as a ``snap``:

.. literalinclude:: /reuse/tutorial/code/task.yaml
    :language: bash
    :start-after: [docs:install-docker]
    :end-before: [docs:install-docker-end]
    :dedent: 2

.. .. warning::
..    There is a `known connectivity issue with LXD and Docker
..    <lxd-docker-connectivity-issue_>`_. If you see a
..    networking issue such as "*A network related operation failed in a context
..    of no network access*", make sure you apply one of the fixes suggested
..    `here <lxd-docker-connectivity-issue_>`_.

.. Note that you'll also need a text editor. You can either install one of your
.. choice or simply use one of the already existing editors in your Ubuntu
.. environment (like ``vi`` or ).

.. _`lxd-docker-connectivity-issue`: https://documentation.ubuntu.com/lxd/en/latest/howto/network_bridge_firewalld/#prevent-connectivity-issues-with-lxd-and-docker
.. _`install-multipass`: https://multipass.run/docs/how-to-install-multipass
.. _`multipass-landing`: https://multipass.run/
