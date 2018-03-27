import numpy as np
from scipy import integrate
import copy
import time

class Model(list):
    """
    The model class inherits from a list.
      The user made reaction classes are appended to this self list.

    When the model is run it uses only:
      self.parameters
      self.species_names
      self.species_starting_values

    When the model is run, it calls integrate.odeint(self.deriv, y0, self.time).
      self.deriv(self, y, t) runs each reaction_class.reaction(y, self.species_names, self.parameters) in turn,
        with the output added to y_prime as the relevent index (determined by self.species_names)

    Each reaction class contains parameter_defaults and parameter_bounds.
      These are used to set self.parameter_defaults and self.parameter_bounds, when self.set_parameters_from_reactions() is called.

    Species are set using the set_species_defaults and set_species_bounds functions.

    """

    def __init__(self):
        # Model inherits from list - reaction classes are held in this self list.
        super(Model, self).__init__()

        """ Time """
        self.start = 0
        self.end = 100
        self.steps = 100
        self.mxsteps = 10000
        self.time = np.linspace(self.start, self.end, self.steps)

        """ Species - used to reset the model, or as the bounds to run ua/sa """
        self.species_defaults = {}
        self.species_bounds = {}

        """ Parameters - used to reset the model, or as the bounds to run ua/sa.  Set by self.set_parameters_from_reactions() """
        self.parameter_defaults = {}
        self.parameter_bounds = {}

        """ Species and parameters used when the model is ran. These are changed each run when doing ua/sa """
        """
        self.species_names and self.species_starting_values are corresponding ordered lists 
        The order of these lists will be same as y and y_prime when the model is run
        This allows index of substrates in y or y_prime to be looked up using the substrate name.
        self.species_names and self.species_starting_values are updated for each run when doing ua/sa.
        """
        self.species = {}
        self.species_names = []
        self.species_starting_values = []

        """
        self.parameters is a dictionary which is passed into each rate equation function when the model is run.
        Parameters are accessed from this dictionary by the rate functions.
        This facilitates sampling the parameter space for ua/sa, rather than setting the parameters in the rate functions themselves.
        self.parameters is updated for each run when doing ua/sa
        """
        self.parameters = {}

    # Time
    def set_time(self, start, end, steps, mxsteps=10000):
        """
        This function sets all the time parameters for the model.

        :param start: integer - the start time - usually 0
        :param end: integer - the end time
        :param steps: integer - the number of timepoints for the output
        :param mxsteps: integer - the max number of steps that should be used to solve the odes
        """
        self.start = start
        self.end = end
        self.steps = steps
        self.mxsteps = mxsteps

        self.time = np.linspace(self.start, self.end, self.steps)

    # Parameters
    def set_parameter_defaults(self, parameters):
        """
        Set self.parameters and self.parameter_defaults

        :param parameters: dict - {"parameter_name" : parameter value, ..}
        """
        self.parameters = parameters
        self.parameter_defaults = copy.deepcopy(parameters)

    def update_parameters(self, parameters):
        """
        Updates the self.parameters dictionary parameters

        :param parameters: dict of format {"parameter_name: : parameter_value, ..}
        """
        self.parameters.update(parameters)

    def set_parameters_from_reactions(self):
        """
        Sets all the parameter variables from those set in the reaction classes

        For each reaction_class, updates self.parameters, self_parameter_defaults and self.parameter_bounds,
        with the dictionaries held in each reaction_class.
        This will add new keys, or overwrite existing ones.
        """

        self.parameters = {}
        self.parameter_defaults = {}
        self.parameter_bounds = {}

        for reaction_class in self:
            self.parameters.update(reaction_class.parameter_defaults)
            self.parameter_defaults.update(copy.deepcopy(reaction_class.parameter_defaults))
            self.parameter_bounds.update(reaction_class.parameter_bounds)

    # Species
    def set_species_defaults(self, species_defaults):
        """
        Sets self.species_defaults, and calls self.update_species to set self.species_names and self.species_starting_values

        :param species_defaults: dictionary - {"specie_name" : specie_value, ..}
        """
        self.species_defaults = species_defaults
        self.species = copy.deepcopy(species_defaults)
        self.update_species(species_defaults)

    def set_species_bounds(self, species_bounds):
        """
        Set self.species_bounds

        :param species_bounds: dictionary - {"species_name" : (lower_bound, upper_bound), ..}
        """

        self.species_bounds = species_bounds

    def update_species(self, species_dict):
        """
        Set the ordered lists self.species_names and self.species_starting_values - used to run the model

        :param species_dict: dictionary - {"specie_name" : species_value, ..}
        """
        self.species.update(species_dict)
        self.species_names, self.species_starting_values = get_species_positions(self.species)

    # Run the model
    def deriv(self, y, t):
        """
        deriv function called by integrate.odeint(self.deriv, y0, self.time)

        For each step when the model is run, the rate for each reaction is calculated and changes in substrates and products calculated.
        These are returned by this function as y_prime, which are added to y which is returned by run_model

        :param y: ordered list of substrate values at this current timepoint. Has the same order as self.substrate_names
        :param t: time, not used in this function but required for some reason
        :return: y_prime - ordered list the same as y, y_prime is the new set of y's for this timepoint.
        """

        yprime = np.zeros(len(y))

        for reaction_class in self:
            yprime += reaction_class.reaction(y, self.species_names, self.parameters)

        return yprime

    def run_model(self):
        """
        Runs the model and outputs y

        This will use self.species_names, self.species_starting_values and self.parameters to run the model.

        Outputs y which is a numpy array of 2 dimensions.
          The first dimension gives a list of all the substrate concentrations at that timepoint.
          The first dimension is the same size as self.time.
          Each index in self.time relates to an index in the first dimension of y.

          eg.  y[0] will return a list of all the starting substrate concentrations
               y[1] gives the substrate concentrations at the first timepoints

               y[0][2] gives the substrate concentration of the second substrate at the first timepoint.

        :return: y - a numpy array of 2 dimensions. Time by substrate.
        """
        y0 = np.array(self.species_starting_values)
        y = integrate.odeint(self.deriv, y0, self.time, mxstep=self.mxsteps)

        return y

    # Reset the model back to default settings
    def reset_model(self):
        """
        Reset the model back to the default settings

        This uses self.species_defaults and self.parameter_defaults
          to set self.species_names, self.species_starting_values and self.parameters
          back to the original default settings.  These the variables used to run the model.
        """

        time.sleep(1)
        self.species = self.species_defaults
        self.species_names, self.species_starting_values = get_species_positions(self.species)
        self.parameters = self.parameter_defaults


"""Functions for formatting species and parameters dicts to the correct format"""
def get_species_positions(species):
    """
    Returns two ordered lists, species_names and species_values

    This function is used by the Model class to set its
      variables for self.species_names and self.species_starting_values.
    These lists are used when the model is run.

    This function is called in the Model class by its functions:
     self.set_species_defaults(species_defaults), and self.update_species(species_dict)

    Given a dictionary of the format {"Specie name" : value for specie starting conc}
    Returns two lists with the same order.
       The first of the species names, the second of the starting values.
       
    :param species: a dictionary of the format {"Specie name" : value for specie starting conc}
    :return: Returns a tuple of two lists with the same order. The first of the species names, the second of the starting values.
    """

    species_names = []
    species_starting_values = []

    for name in species:
        species_names.append(name)
        if type(species[name]) == list:
            species_starting_values.append(species[name][0])
        else:
            species_starting_values.append(species[name])

    return species_names, species_starting_values

def set_parameter_defaults(parameters_with_error):
    """
    Returns parameter dictionary without the error

    Takes a dictionary of {"Paramater name" : (default_param_value, error_value)}
    Returns a new dictinary without the error. So {"Paramater name" : default_param_value}
    This is the format the model uses to run.

    :param parameters_with_error: dict {"Paramater name" : (default_param_value, error_value)}
    :return: dict {"Paramater name" : default_param_value}
    """

    parameters = {}
    for name in parameters_with_error:
        parameters[name] = parameters_with_error[name][0]

    return parameters

def set_species_defaults(species_with_error):
    """
    Returns species_dictionary without the error

    Takes a dictionary of {"Specie name" : (default_specie_value, error_value)}
        Returns a new dictinary without the error. So {"Specie name" : default_specie_value}
        This is the format the model uses to run.

    The function should also be able to take a dictionary without the error if this is entered by mistake.

    :param species_with_error: dict with format {"Specie name" : (default_specie_value, error_value)}
    :return: dict with format {"Specie name" : default_specie_value}
    """

    species = {}
    for name in species_with_error:
        if type(species_with_error[name]) == list or type(species_with_error[name]) == tuple:
            species[name] = species_with_error[name][0]
        else:
            species[name] = species_with_error[name]

    return species


"""Functions to add or substract the rate from yprime at the correct index's"""
def yprime_plus(y_prime, rate, substrates, substrate_names):
    """
    This function is used by the rate classes the user creates.

    It takes the numpy array for y_prime, and adds the amount in rate to all the substrates listed in substrates
    Returns the new y_prime

    :param y_prime: a numpy array for the substrate values, the same order as y
    :param rate:   the rate calculated by the user made rate equation
    :param substrates: list of substrates for which rate should be added
    :param substrate_names: the ordered list of substrate names in the model.  Used to get the position of each substrate in y_prime
    :return: y_prime: following the addition of rate to the specificed substrates
    """

    for name in substrates:
        y_prime[substrate_names.index(name)] += rate

    return y_prime

def yprime_minus(y_prime, rate, substrates, substrate_names):
    """
    This function is used by the rate classes the user creates.

    It takes the numpy array for y_prime, and subtracts the amount in rate to all the substrates listed in substrates
    Returns the new y_prime

    :param y_prime: a numpy array for the substrate values, the same order as y
    :param rate:   the rate calculated by the user made rate equation
    :param substrates: list of substrates for which rate should be subtracted
    :param substrate_names: the ordered list of substrate names in the model.  Used to get the position of each substrate in y_prime
    :return: y_prime: following the subtraction of rate to the specificed substrates
    """
    for name in substrates:
        y_prime[substrate_names.index(name)] -= rate

    return y_prime

def calculate_yprime(y, rate, substrates, products, substrate_names):
    """
    This function is used by the rate classes the user creates.

    It takes the numpy array for y_prime,
      and adds or subtracts the amount in rate to all the substrates or products listed
    Returns the new y_prime

    :param y_prime: a numpy array for the substrate values, the same order as y
    :param rate:   the rate calculated by the user made rate equation
    :param substrates: list of substrates for which rate should be subtracted
    :param products: list of products for which rate should be added
    :param substrate_names: the ordered list of substrate names in the model.  Used to get the position of each substrate or product in y_prime
    :return: y_prime: following the addition or subtraction of rate to the specificed substrates
    """

    y_prime = np.zeros(len(y))

    for name in substrates:
        y_prime[substrate_names.index(name)] -= rate

    for name in products:
        y_prime[substrate_names.index(name)] += rate

    return y_prime
