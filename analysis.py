import re
import subprocess
from itertools import product
import pandas as pd


class PyRatGame:
    """
    Utility class to run a PyRat game from within python, and get back
    statistics to analyze.

    It activates the "--nodrawing" and "--synchronous" flags by default, so
    experiments run quicker.

    Example
    -------

    You can set parameters at creation time, or set then as attributes later,
    so it is easy to re-run the same configuration with minimal change.

    >>> pyrat = PyRatGame(width=13, height=13, pieces=1, tests=10)
    >>>
    >>> pyrat.rat = "AIs/lab3_bfs.py"
    >>> csv_path_bfs, stats_bfs = pyrat.run()
    >>>
    >>> pyrat.rat = "AIs/lab4_dijkstra.py"
    >>> csv_path_dijkstra, stats_dijkstra = pyrat.run()
    """

    csv_path_pattern = re.compile(
        r"^Stats can be found at: (?P<csv_path>.*?\.csv)$",
        flags=re.MULTILINE,
    )

    def __init__(self, **kwargs):
        default_kwargs = {"synchronous": True, "nodrawing": True}
        # by-pass redefined __setattr__
        super().__setattr__("kwargs", {**default_kwargs, **kwargs})

    def run(self):
        completed = subprocess.run(self.cmd_line_args, capture_output=True)
        csv_path = self._extract_csv_path(completed.stdout.decode())
        return csv_path, self.load_stats(csv_path)

    @staticmethod
    def load_stats(csv_path):
        return pd.read_csv(csv_path, skiprows=2)

    @property
    def cmd_line_args(self):
        args = ["python", "pyrat.py"]
        for name, value in self.kwargs.items():
            if isinstance(value, bool) and value is True:
                args.append("--" + name)
            else:
                args.append("--" + name)
                args.append(str(value))
        return args

    @classmethod
    def _extract_csv_path(cls, stdout):
        return cls.csv_path_pattern.search(stdout).groupdict()["csv_path"]

    def __setattr__(self, name, value):
        """
        Allows to modify `kwargs` on `pyrat` `PyRatGame` instance with:
            `pyrat.width = 34`
        rather than:
            `pyrat.kwargs["width"] = 34`
        """
        self.kwargs.update({name: value})


def pyrat_multiruns(*, fixed_params, grid_params, link_height_width=False):
    """Run multiple instances of PyRatGame, for all combinations of parameters
    given in `grid_params`.

    Parameters
    ----------
    fixed_params : dict[str, Any]
        The parameters to be shared across runs.
    grid_params : dict[str, list[Any]]
        The parameters from which to take all combinations from.
        E. g. `grid_params = {"width": [5, 10, 15], "density": [0.2, 0.4]}`
        will run 3*2 = 6 experiments.
    link_height_width: bool (default: `False`)
        Wether to recopy "width" parameter into "height" parameter, so only one
        need to be given in `grid_params` and the maze will a square.

    Returns
    -------
    pd.DataFrame
        The synthesis of all runs.
    """

    params_keys = tuple(grid_params.keys())

    # Create a game instance with only fixed parameters
    pyrat = PyRatGame(**fixed_params)

    # Run experiments by iterating over configurations
    results = {}
    for params in dict_product(grid_params):
        for pname, pvalue in params.items():
            pyrat.kwargs[pname] = pvalue
            if link_height_width:
                if pname == "height":
                    pyrat.kwargs["width"] = pvalue
                if pname == "width":
                    pyrat.kwargs["height"] = pvalue

        csv_path, stats = pyrat.run()

        # Let's just take the mean across tests
        stats = stats.mean()

        # # And reduce to the variables of interest
        # if variables:
        #     stats = stats[variables]

        # Register, converting Path() objects to str(Path().stem)
        pvalues = tuple(
            pvalue if pname not in {"rat", "python"} else str(pvalue.stem)
            for pname, pvalue in params.items()
        )
        results[pvalues] = stats

    # Aggregate results in a single dataframe
    df = pd.DataFrame(results).T  # variables as columns, params as rows
    df.index.names = params_keys

    return df


def dict_product(d):
    keys = list(d.keys())
    for pms in product(*d.values()):
        yield dict(zip(keys, pms))


def comparison_plot(stats, variable, lines, ax=None, **fixed):
    """Make a comparison plot from results obtained using `pyrat_multiruns`.

    From all parameters used as `params_grid` to construct the `stats` dataframe
    with `pyrat_multiruns`, exactly all but one should be mentionned either in
    the `lines` argument or in the `fixed` keyword arguments.

    Parameters
    ----------
    df : pd.DataFrame
        The dataframe obtained using `pyrat_multiruns`.
    variable : str
        The variable to study, plotted on the y-axis.
    lines : str
        The parameter (one of them given as `params_grid` in `pyrat_multiruns`)
        from which to draw multiple lines for each of its values.
    ax : plt.Axes, optional
        An ax to draw on. Convenient to put the plot into a subplot.

    Returns
    -------
    plt.Axes
        The ax where the plot was drawn.
    """
    stats = stats[variable]
    for param, value in fixed.items():
        stats = stats.xs(value, level=param)
    if lines is not None:
        stats = stats.unstack(lines)
    ax = stats.plot(ylabel=variable, title=str(fixed), grid=True, marker="o", ax=ax)
    return ax
