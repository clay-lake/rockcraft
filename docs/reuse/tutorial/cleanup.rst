You've reached the end of this tutorial.

You can leave the virtual machine by issuing the following command:

.. code-block:: bash

    logout

Reset your environment
======================

If you would like to remove this virtual machine ``multipass delete -p`` will
remove the virtual machine and any related files. 

.. code-block:: bash

    multipass delete -p rock-dev

If your home directory was mounted during this tutorial, your project files will
be preserved.