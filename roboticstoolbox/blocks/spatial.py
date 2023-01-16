import numpy as np
from math import sin, cos, pi

# import matplotlib.pyplot as plt
import time
from spatialmath import base, SE3

from bdsim.components import TransferBlock, FunctionBlock, SourceBlock
from bdsim.graphics import GraphicsBlock

from roboticstoolbox import quintic_func, trapezoidal_func

class Tr2Delta(FunctionBlock):
    """
    :blockname:`TR2DELTA`

    .. table::
       :align: left

    +------------+------------+---------+
    | inputs     | outputs    |  states |
    +------------+------------+---------+
    | 2          | 1          | 0       |
    +------------+------------+---------+
    | SE3, SE3   | ndarray(6) |         |
    +------------+------------+---------+
    """

    nin = 2
    nout = 1
    inlabels = ('T1', 'T2')
    outlabels = ('Δ',)

    def __init__(self, **blockargs):
        """
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: a TR2DELTA block
        :rtype: Tr2Delta instance

        Difference between T1 and T2 as a 6-vector

        The block has two input port:

            1. T1 as an SE3.
            2. T2 as an SE3.

        and one output port:

            1. delta as an ndarray(6,n)

        :seealso: :func:`spatialmath.base.tr2delta`
        """
        super().__init__(**blockargs)

        self.inport_names(("T1", "T2"))
        self.outport_names(("$\delta$",))

    def output(self, t=None):
        return [base.tr2delta(self.inputs[0].A, self.inputs[1].A)]


# ------------------------------------------------------------------------ #


class Delta2Tr(FunctionBlock):
    """
    :blockname:`DELTA2TR`

    .. table::
       :align: left

    +------------+----------+---------+
    | inputs     | outputs  |  states |
    +------------+----------+---------+
    | 1          | 1        | 0       |
    +------------+----------+---------+
    | ndarray(6) | SE3      |         |
    +------------+----------+---------+
    """

    nin = 1
    nout = 1
    outlabels = ('T',)
    inlabels = ('Δ',)

    def __init__(self, **blockargs):
        """
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: a DELTA2TR block
        :rtype: Delta2Tr instance

        Delta to SE(3)

        The block has one input port:

            1. delta as an ndarray(6,n)

        and one output port:

            1. T as an SE3

        :seealso: :func:`spatialmath.base.delta2tr`
        """
        super().__init__(**blockargs)

        self.inport_names(("$\delta$",))
        self.outport_names(("T",))

    def output(self, t=None):
        return [SE3.Delta(self.inputs[0])]


# ------------------------------------------------------------------------ #

class Point2Tr(FunctionBlock):
    """
    :blockname:`POINT2TR`

    .. table::
       :align: left

    +------------+----------+---------+
    | inputs     | outputs  |  states |
    +------------+----------+---------+
    | 1          | 1        | 0       |
    +------------+----------+---------+
    | ndarray(3) | SE3      |         |
    +------------+----------+---------+
    """

    nin = 1
    nout = 1

    def __init__(self, T, **blockargs):
        """
        :param T: the transform
        :type T: SE3
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: a POINT2TR block
        :rtype: Point2Tr instance

        The block has one input port:

            1. a 3D point as an ndarray(3)

        and one output port:

            1. T as an SE3 with its position part replaced by the input

        :seealso: :func:`spatialmath.base.delta2tr`
        """
        super().__init__(**blockargs)

        self.inport_names(("t",))
        self.outport_names(("T",))
        self.pose = T

    def output(self, t=None):
        T = SE3.Rt(self.pose.R, t=self.inputs[0])
        return [T]


# ------------------------------------------------------------------------ #


class TR2T(FunctionBlock):
    """
    :blockname:`TR2T`

    .. table::
       :align: left

    +------------+----------+---------+
    | inputs     | outputs  |  states |
    +------------+----------+---------+
    | 1          | 3        | 0       |
    +------------+----------+---------+
    | SE3        | float    |         |
    +------------+----------+---------+
    """

    nin = 1
    nout = 3
    inlabels = ('T',)
    outlabels = ('x', 'y', 'z')

    def __init__(self, **blockargs):
        """
        :param T: the transform
        :type T: SE3
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: a POINT2TR block
        :rtype: Point2Tr instance

        The block has one input port:

            1. a 3D point as an ndarray(3)

        and one output port:

            1. T as an SE3 with its position part replaced by the input

        :seealso: :func:`spatialmath.base.delta2tr`
        """
        super().__init__(**blockargs)

        self.inport_names(("T",))
        self.outport_names(("x", "y", "z"))

    def output(self, t=None):
        t = self.inputs[0].t
        return list(t)

# ------------------------------------------------------------------------ #


class Traj(FunctionBlock):
    """
    :blockname:`TRAJ`

    .. table::
       :align: left

    +------------+---------+---------+
    | inputs     | outputs |  states |
    +------------+---------+---------+
    | 0 or 1     | 1       | 0       |
    +------------+---------+---------+
    | float      | float   |         |
    +------------+---------+---------+
    """

    nin = -1
    nout = 3
    outlabels = ('q',)

    def __init__(self, y0=0, yf=1, T=None, time=False, traj="trapezoidal", **blockargs):
        """

        :param y0: initial value, defaults to 0
        :type y0: array_like(m), optional
        :param yf: final value, defaults to 1
        :type yf: array_like(m), optional
        :param T: time vector or number of steps, defaults to None
        :type T: array_like or int, optional
        :param time: x is simulation time, defaults to False
        :type time: bool, optional
        :param traj: trajectory type, one of: 'trapezoidal' [default], 'quintic'
        :type traj: str, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: TRAJ block
        :rtype: Traj instance

        Create a trajectory block.

        A block that generates a trajectory using a trapezoidal or quintic
        polynomial profile.

        """
        self.time = time
        if time:
            nin = 1
            blockclass = "function"
        else:
            nin = 0
            blockclass = "source"
            
        super().__init__(nin=nin, blockclass=blockclass, **blockargs)

        y0 = base.getvector(y0)
        yf = base.getvector(yf)
        assert len(y0) == len(yf), "y0 and yf must have same length"

        self.y0 = y0
        self.yf = yf
        self.time = time
        self.T = T
        self.traj = traj

        self.outport_names(("y", "yd", "ydd"))

    def start(self, **blockargs):
        if self.time:
            assert self.x[0] <= 0, "interpolation not defined for t=0"
            assert self.x[-1] >= self.bd.T, "interpolation not defined for t=T"

        if self.traj == "trapezoidal":
            trajfunc = trapezoidal_func
        elif self.traj == "quintic":
            trajfunc = quintic_func

        self.trajfuncs = []
        for i in range(len(self.y0)):
            self.trajfuncs.append(trajfunc(self.y0[i], self.yf[i], self.T))

    def output(self, t=None):
        if self.time:
            t = self.inputs[0]

        out = []
        for i in range(len(self.y0)):
            out.append(self.trajfuncs[i](t))

        # we have a list of tuples out[i][j]
        # i is the timestep, j is y/yd/ydd
        y = [o[0] for o in out]
        yd = [o[1] for o in out]
        ydd = [o[2] for o in out]

        return [np.hstack(y), np.hstack(yd), np.hstack(ydd)]

# ------------------------------------------------------------------------ #

class JTraj(SourceBlock):
    """
    :blockname:`JTRAJ`

    .. table::
       :align: left

    +------------+------------+---------+
    | inputs     | outputs    |  states |
    +------------+------------+---------+
    | 0          | 3          | 0       |
    +------------+------------+---------+
    |            | ndarray(n) |         |
    +------------+------------+---------+
    """

    nin = 0
    nout = 3
    outlabels = ('q', 'qd', 'qdd')

    def __init__(self, q0, qf, qd0=None, qdf=None, T=None, **blockargs):
        """
        Compute a joint-space trajectory

        :param q0: initial joint coordinate
        :type q0: array_like(n)
        :param qf: final joint coordinate
        :type qf: array_like(n)
        :param T: time vector or number of steps, defaults to None
        :type T: array_like or int, optional
        :param qd0: initial velocity, defaults to None
        :type qd0: array_like(n), optional
        :param qdf: final velocity, defaults to None
        :type qdf: array_like(n), optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: TRAJ block
        :rtype: Traj instance

        - ``tg = jtraj(q0, qf, N)`` is a joint space trajectory where the joint
        coordinates vary from ``q0`` (M) to ``qf`` (M).  A quintic (5th order)
        polynomial is used with default zero boundary conditions for velocity and
        acceleration.  Time is assumed to vary from 0 to 1 in ``N`` steps.

        - ``tg = jtraj(q0, qf, t)`` as above but ``t`` is a uniformly-spaced time
        vector

        The return value is an object that contains position, velocity and
        acceleration data.

        Notes:

        - The time vector, if given, scales the velocity and acceleration outputs
        assuming that the time vector starts at zero and increases
        linearly.

        :seealso: :func:`ctraj`, :func:`qplot`, :func:`~SerialLink.jtraj`
        """
        super().__init__(**blockargs)
        self.type = "source"
        self.outport_names(
            (
                "q",
                "qd",
                "qdd",
            )
        )

        q0 = base.getvector(q0)
        qf = base.getvector(qf)

        if not len(q0) == len(qf):
            raise ValueError("q0 and q1 must be same size")

        if qd0 is None:
            qd0 = np.zeros(q0.shape)
        else:
            qd0 = getvector(qd0)
            if not len(qd0) == len(q0):
                raise ValueError("qd0 has wrong size")
        if qdf is None:
            qdf = np.zeros(q0.shape)
        else:
            qd1 = getvector(qdf)
            if not len(qd1) == len(q0):
                raise ValueError("qd1 has wrong size")

        self.q0 = q0
        self.qf = qf
        self.qd0 = qd0
        self.qdf = qf

        # call start now, so that output works when called by compile
        # set T to 1 just for now
        if T is None:
            self.T = 1
        self.start()
        self.T = T
        

    def start(self, state=None):

        if self.T is None:
            # use simulation tmax
            self.T = state.T

        tscal = self.T
        self.tscal = tscal

        q0 = self.q0
        qf = self.qf
        qd0 = self.qd0
        qdf = self.qdf

        # compute the polynomial coefficients
        A = 6 * (qf - q0) - 3 * (qdf + qd0) * tscal
        B = -15 * (qf - q0) + (8 * qd0 + 7 * qdf) * tscal
        C = 10 * (qf - q0) - (6 * qd0 + 4 * qdf) * tscal
        E = qd0 * tscal
        F = q0

        self.coeffs = np.array([A, B, C, np.zeros(A.shape), E, F])
        self.dcoeffs = np.array(
            [np.zeros(A.shape), 5 * A, 4 * B, 3 * C, np.zeros(A.shape), E]
        )
        self.ddcoeffs = np.array(
            [
                np.zeros(A.shape),
                np.zeros(A.shape),
                20 * A,
                12 * B,
                6 * C,
                np.zeros(A.shape),
            ]
        )

    def output(self, t=None):

        tscal = self.tscal
        ts = t / tscal
        tt = np.array([ts ** 5, ts ** 4, ts ** 3, ts ** 2, ts, 1]).T

        qt = tt @ self.coeffs

        # compute  velocity
        qdt = tt @ self.dcoeffs / tscal

        # compute  acceleration
        qddt = tt @ self.ddcoeffs / tscal ** 2

        return [qt, qdt, qddt]

# ------------------------------------------------------------------------ #

class LSPB(SourceBlock):
    """
    :blockname:`LSPB`

    .. table::
       :align: left

    +------------+------------+---------+
    | inputs     | outputs    |  states |
    +------------+------------+---------+
    | 0          | 3          | 0       |
    +------------+------------+---------+
    |            | float      |         |
    +------------+------------+---------+
    """

    nin = 0
    nout = 3
    outlabels = ('q', 'qd', 'qdd')

    def __init__(self, q0, qf, V=None, T=None, **blockargs):
        """
        Compute a joint-space trajectory

        :param q0: initial joint coordinate
        :type q0: array_like(n)
        :param qf: final joint coordinate
        :type qf: array_like(n)
        :param T: time vector or number of steps, defaults to None
        :type T: array_like or int, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: LSPB block
        :rtype: LSPB instance

        - ``tg = jtraj(q0, qf, N)`` is a joint space trajectory where the joint
        coordinates vary from ``q0`` (M) to ``qf`` (M).  A quintic (5th order)
        polynomial is used with default zero boundary conditions for velocity and
        acceleration.  Time is assumed to vary from 0 to 1 in ``N`` steps.

        - ``tg = jtraj(q0, qf, t)`` as above but ``t`` is a uniformly-spaced time
        vector

        The return value is an object that contains position, velocity and
        acceleration data.

        Notes:

        - The time vector, if given, scales the velocity and acceleration outputs
        assuming that the time vector starts at zero and increases
        linearly.

        :seealso: :func:`ctraj`, :func:`qplot`, :func:`~SerialLink.jtraj`
        """
        super().__init__(nout=3, **blockargs)
        self.type = "source"
        self.T = T
        self.q0 = q0
        self.qf = qf

    def start(self):

        if self.T is None:
            self.T = self.bd.state.T
        self.trapezoidalfunc = trapezoidal_func(self.q0, self.qf, self.T)

    def output(self, t=None):
        return list(self.trapezoidalfunc(t))

# ------------------------------------------------------------------------ #

class CTraj(SourceBlock):
    """
    :blockname:`CTRAJ`

    .. table::
       :align: left

    +------------+---------+---------+
    | inputs     | outputs |  states |
    +------------+---------+---------+
    | 0          | 1       | 0       |
    +------------+---------+---------+
    |            | float   |         |
    +------------+---------+---------+
    """

    nin = 0
    nout = 1
    outlabels = ('T',)

    def __init__(
        self,
        T1,
        T2,
        T,
        trapezoidal=True,
        **blockargs
    ):
        """
        [summary]

        :param T1: initial pose
        :type T1: SE3
        :param T2: final pose
        :type T2: SE3
        :param T: motion time
        :type T: float
        :param trapezoidal: Use LSPB motion profile along the path
        :type trapezoidal: bool
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: CTRAJ block
        :rtype: CTraj instance

        Create a Cartesian motion block.

        The block outputs a pose that varies smoothly from ``T1`` to ``T2`` over
        the course of ``T`` seconds.
        
        If ``T`` is not given it defaults to the simulation time.

        If ``trapezoidal`` is True then a trapezoidal motion profile is used along the path
        to provide initial acceleration and final deceleration.  Otherwise,
        motion is at constant velocity.

        :seealso: :method:`SE3.interp`

        """

        # TODO
        # flag to rotate the frame rather than just translate it
        super().__init__(**blockargs)

        self.T1 = T1
        self.T2 = T2
        self.T = T
        self.trapezoidal = trapezoidal

    def start(self, state):
        if self.T is None:
            self.T = self.bd.state.T
        if self.trapezoidal:
            self.trapezoidalfunc = trapezoidal_func(0.0, 1.0, self.T)

    def output(self, t=None):
        if self.trapezoidal:
            s = self.trapezoidalfunc(t)
        else:
            s = np.min(t / self.T, 1.0)

        return [self.T1.interp(self.T2, s)]


# ------------------------------------------------------------------------ #

class CirclePath(SourceBlock):
    """
    :blockname:`CIRCLEPATH`

    .. table::
       :align: left

    +------------+---------+---------+
    | inputs     | outputs |  states |
    +------------+---------+---------+
    | 0 or 1     | 1       | 0       |
    +------------+---------+---------+
    | float      | float   |         |
    +------------+---------+---------+
    """

    nin = 0
    nout = 1

    def __init__(
        self,
        radius=1,
        centre=(0, 0, 0),
        pose=None,
        frequency=1,
        unit="rps",
        phase=0,
        **blockargs
    ):
        """

        :param radius: radius of circle, defaults to 1
        :type radius: float
        :param centre: center of circle, defaults to [0,0,0]
        :type centre: array_like(3)
        :param pose: SE3 pose of output, defaults to None
        :type pose: SE3
        :param frequency: rotational frequency, defaults to 1
        :type frequency: float
        :param unit: unit for frequency, one of: 'rps' [default], 'rad'
        :type unit: str
        :param phase: phase
        :type phase: float
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        :return: TRAJ block
        :rtype: Traj instance

        Create a circular motion block.

        The block outputs the coordinates of a point moving in a circle of
        radius ``r`` centred at ``centre`` and parallel to the xy-plane.

        By default the output is a 3-vector :math:`(x, y, z)` but if 
        ``pose`` is an ``SE3`` instance the output is a copy of that pose with
        its translation set to the coordinate of the moving point.  This is the
        motion of a frame with fixed orientation following a circular path.

        """

        # TODO
        # flag to rotate the frame rather than just translate it
        super().__init__(**blockargs)

        if unit == "rps":
            omega = frequency * 2 * pi
            phase = phase * 2 * pi
        elif unit == "rad":
            omega = frequency

            # Redundant assignment, commented for LGTM
            # phase = phase
        else:
            raise ValueError("bad units: rps or rad")

        self.radius = radius
        assert len(centre) == 3, "centre must be a 3 vector"
        self.centre = centre
        self.pose = pose
        self.omega = omega
        self.phase = phase

        self.outport_names(("y",))

    def output(self, t=None):
        theta = t * self.omega + self.phase
        x = self.radius * cos(theta) + self.centre[0]
        y = self.radius * sin(theta) + self.centre[1]
        p = (x, y, self.centre[2])

        if self.pose is not None:
            pp = SE3.Rt(self.pose.R, p)
            p = pp

        return [p]

if __name__ == "__main__":

    from pathlib import Path

    exec(
        open(
            Path(__file__).parent.parent.parent.absolute() / "tests" / "test_blocks.py"
        ).read()
    )
