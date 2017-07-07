The Plugin Structure
====================

The the plugin code may inherit from :class:`csmpe.CSMPlugin` class. This is not mandatory,
however the plugin code must be able to accept the PluginContext object in the constructor
and must contain at least four attributes described below.

.. automodule:: csmpe

CSMPlugin Class
---------------

.. autoclass:: CSMPlugin

    .. autoattribute:: name
    .. autoattribute:: phases
    .. autoattribute:: platforms
    .. autoattribute:: os

    .. automethod:: __init__
    .. automethod:: run


The plugin package structure
----------------------------

The plugin package must consist of the plugin code and setup.py installation script.


The sample plugin package is show below.

.. code-block:: text

    plugin
    |
    +-- sample_plugin
    |   |
    |   +-- __init__.py
    |   |
    +   +-- plugin.py
    |
    +-- setup.py


The sample setup.py file is shown below:

.. code-block:: python

    from setuptools import setup, find_packages
    from uuid import uuid4

    # The required packages should be listed here
    install_requires = [
    ]


    setup(
        name='sample_plugin',
        version='0.0.1',
        description='Sample Plugin',
        author='Klaudiusz Staniek',
        author_email='klstanie [at] cisco.com',
        url='',
        packages=find_packages(),
        entry_points={
            'csm.plugin': [
                '{} = sample_plugin.plugin:Plugin'.format(uuid4()),
            ],
        },
        zip_safe=True,
        install_requires=install_requires,
    )


The ``entry_point`` is the most important and mandatory attribute. The Plugin Engine search for all the packages
matching the ``csm.plugin`` entry point group name. The entry point should be unique and in the above example the
unique UUID is being calculated.

Each plugin package may have one or more entry points provided. It allows the plugins handling
multiple platforms or operating system being grouped together into a single package.

The sample plugin code is shown below:

.. code-block:: python

    from csmpe import CSMPlugin

    class Plugin(CSMPlugin):
        """This is a sample plugin"""
        name = "Sample Plugin"
        platforms = {'ASR9K'}
        phases = {'Pre-Check'}
        os = {'IOS XR's}

        def run(self):
            self.ctx.info("Sample Plugin is running")