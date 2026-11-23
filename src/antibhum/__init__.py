"""AntiBHum public interface; requires the binary distribution."""

__version__ = "0.1.4"

def run_humanization(*args, **kwargs):
    """Run humanization using the installed native core."""
    from ._core import run_humanization as run
    return run(*args, **kwargs)
