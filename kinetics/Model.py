import numpy as np
import pandas as pd
from scipy import integrate
import copy
import matplotlib.pyplot as plt

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

    def __init__(self, logging=True):
        # Model inherits from list - reaction classes are held in this self list.
        super(Model, self).__init__()

        """ Time """
        self.start = 0
        self.end = 100
        self.steps = 100
        self.mxsteps = 10000
        self.time = np.linspace(self.start, self.end, self.steps)

        """ Species - used to reset the model, or as the bounds to run ua/sa """
        self.species = {}
        self.species_distributions = {}

        """ Parameters - used to reset the model, or as the bounds to run ua/sa.  Set by self.set_parameters_from_reactions() """
        self.parameters = {}
        self.parameter_distributions = {}

        """ Species and parameters used when the model is ran. These are changed each run when doing ua/sa """
        self.run_model_species = {}
        self.run_model_species_names = []
        self.run_model_species_starting_values = []
        self.run_model_parameters = {}

        self.y = []

        self.logging = logging

    # Time
    def set_time(self, start, end, steps):
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
        self.time = np.linspace(self.start, self.end, self.steps)

    # Parameters
    def set_parameters_from_reactions(self):
        """
        Sets all the parameter variables from those set in the reaction classes

        For each reaction_class, updates self.parameters, self_parameter_defaults and self.parameter_bounds,
        with the dictionaries held in each reaction_class.
        This will add new keys, or overwrite existing ones.
        """

        self.parameters = {}
        self.parameter_distributions = {}
        self.run_model_parameters = {}

        if self.logging == True:
            print('-- Set unspecified parameters defaults to the means of distributions: --')

        for reaction_class in self:
            if reaction_class.parameters == {}:
                reaction_class.set_parameter_defaults_to_means()
                if self.logging==True:
                    print(reaction_class.parameters)

            self.run_model_parameters.update(reaction_class.parameters)
            self.parameters.update(copy.deepcopy(reaction_class.parameters))
            self.parameter_distributions.update(reaction_class.parameter_distributions)

    # Species
    def update_species(self, species_dict):
        self.run_model_species.update(species_dict)
        self.run_model_species_names = list(self.run_model_species.keys())
        self.run_model_species_starting_values = list(self.run_model_species.values())

    def load_species_from_reactions(self):
        if self.logging == True:
            print('-- Load unspecified species as default = 0 --')
        for reaction in self:
            for substrate in reaction.substrates + reaction.products + reaction.reaction_substrate_names:
                if substrate not in self.species:
                    self.species[substrate] = 0
                    if self.logging == True:
                        print(str(substrate) + ' ', end='')
        if self.logging == True:
            print()

    def set_species_defaults_to_mean(self):

        for name in self.species_distributions:
            if name not in self.species:
                self.species[name] = self.species_distributions[name].mean()

    # Prepare the model
    def setup_model(self):
        # Species
        self.set_species_defaults_to_mean()
        self.load_species_from_reactions()
        self.update_species(self.species)

        # Parameters
        self.set_parameters_from_reactions()

    def reset_reaction_indexes(self):
        for reaction_class in self:
            reaction_class.reset_reaction()

    def reset_model_to_defaults(self):
        """
        Reset the model back to the default settings

        This uses self.species_defaults and self.parameter_defaults
          to set self.species_names, self.species_starting_values and self.parameters
          back to the original default settings.  These the variables used to run the model.
        """

        self.update_species(self.species)
        self.run_model_parameters = self.parameters
        self.y = []

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
            yprime += reaction_class.reaction(y, self.run_model_species_names, self.run_model_parameters)

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
        y0 = np.array(self.run_model_species_starting_values)
        self.y = integrate.odeint(self.deriv, y0, self.time, mxstep=self.mxsteps)
        self.reset_reaction_indexes()

        return self.y

    # Export results as dataframe and plot
    def results_dataframe(self):
        ys_at_t = {'Time' : self.time}

        for i in range(len(self.run_model_species_names)):
            name = self.run_model_species_names[i]
            ys_at_t[name] = []

            for t in range(len(self.time)):
                ys_at_t[name].append(self.y[t][i])

        df = pd.DataFrame(ys_at_t)

        return df

    def plot_substrate(self, substrate, plot=False):
        ys_at_t = []
        i = self.run_model_species_names.index(substrate)
        for t in range(len(self.time)):
            ys_at_t.append(self.y[t][i])

        plt.plot(self.time, ys_at_t, label=substrate)
        plt.legend()

        if plot == True:
            plt.show()

    # Check parameters when contraining parameter space
    def check_parameter_limits(self):
        all_within_limits = True
        for reaction_class in self:
            if reaction_class.sampling_limits(self.run_model_parameters) == False:
                all_within_limits = False
        return all_within_limits

class Metrics(object):

    def __init__(self, model,
                 substrate='', product='', reaction_volume=1,
                 enzyme_mws={}, species_mws={}):

        self.model = model
        self.substrate = substrate
        self.product = product
        self.reaction_volume = reaction_volume
        self.total_volume = reaction_volume
        self.enzyme_mws = enzyme_mws
        self.species_mws = species_mws

        self.refresh_metrics()

    def refresh_metrics(self, model=False, flow_rate=False):
        if model!=False:
            self.model=model

        if flow_rate != False:
            self.total_volume = (self.model.end * self.model.parameters[flow_rate])/1000 # In L

        self.model.setup_model()
        self.model.run_model()


    def total_enzyme(self):

        total = 0
        for enzyme in self.enzyme_mws:
            conc = self.model.species_defaults[enzyme]
            mol_enzyme = (conc / 1000000) * self.reaction_volume
            g_enzyme = mol_enzyme * self.enzyme_mws[enzyme]
            total += g_enzyme

        return total

    def total_enzyme_concentration(self):

        conc = self.total_enzyme() / self.reaction_volume
        return conc

    def e_factor(self):
        g_waste = 0
        g_product = 0

        df = self.model.results_dataframe()

        for substrate in df:
            if substrate in self.species_mws:
                mol_substrate = ((df[substrate].iloc[-1] * self.total_volume) / 1000000)
                g_substrate = mol_substrate * self.species_mws[substrate]
            elif substrate in self.enzyme_mws:
                mol_substrate = ((df[substrate].iloc[-1] * self.total_volume) / 1000000)
                g_substrate = mol_substrate * self.enzyme_mws[substrate]
            else:
                g_substrate = 0

            if substrate == self.product:
                g_product = g_substrate
            else:
                g_waste += g_substrate

        e_factor = g_waste / g_product

        return e_factor

    def space_time_yield(self):
        # g / L / day   eg 360 g/L/day

        g_product = self.total_product()
        time_taken_days = (self.model.end / (60*24)) # time in days

        sty_per_day = g_product / self.reaction_volume / time_taken_days

        return sty_per_day

    def total_product(self):
        conc_uM = self.product_concentration_uM()
        conc_mM = conc_uM/1000
        conc_M = conc_mM/1000
        mol_product = (conc_M * self.total_volume)
        g_product = mol_product * self.species_mws[self.product]

        return g_product

    def product_concentration_uM(self):
        df = self.model.results_dataframe()
        conc = df[self.product].iloc[-1]

        return conc

    def specific_productivity(self):
        g_product = self.total_product()
        g_enzyme = self.total_enzyme()
        reaction_time = self.reaction_time() / 60 #in hours

        return g_product / g_enzyme / reaction_time


    def biocatalyst_productivity(self):

        df = self.model.results_dataframe()
        mol_product = ((df[self.product].iloc[-1] * self.total_volume) / 1000000)
        g_product = mol_product * self.species_mws[self.product]

        total_g_enzyme = 0
        for enzyme in self.enzyme_mws:
            conc = self.model.species_defaults[enzyme]
            mol_enzyme = (conc / 1000000) * self.reaction_volume
            g_enzyme = mol_enzyme * self.enzyme_mws[enzyme]
            total_g_enzyme += g_enzyme

        biocatalyst_productivity = g_product / total_g_enzyme

        return biocatalyst_productivity

    def substrate_concentration(self):

        df = self.model.results_dataframe()
        mol_substrate = ((df[self.substrate].iloc[0] * self.reaction_volume) / 1000000)
        g_substrate = mol_substrate * self.species_mws[self.substrate]

        conc = g_substrate / self.reaction_volume

        return conc

    def pc_yield(self):

        if self.model.y == []:
            self.refresh_metrics()

        df = self.model.results_dataframe()

        substrate_start = df[self.substrate].iloc[0]
        product_end = df[self.product].iloc[-1]
        final_yield = (product_end/substrate_start)*100

        return final_yield

    def reaction_time(self):
        return self.model.end

    def uncertainty(self, ci=95, num_samples=100, logging=False):
        if self.model.y == []:
            self.refresh_metrics()

        ua = UA(self.model, num_samples=num_samples, quartile_range=ci, logging=logging)
        ua.make_lhc_samples()
        ua.run_models()
        product_df = ua.calculate_df_quartiles_single_substrate(self.product)

        high_end = product_df['High'].iloc[-1]
        low_end = product_df['Low'].iloc[-1]

        return high_end-low_end

def uM_to_mgml(enzyme_mws, species_concs, scale=1000000):

    dict_of_mgml = {}

    for enzyme, mw in enzyme_mws.items():
        vol = 1 # 1L
        conc = species_concs[enzyme] / scale #returns conc in M

        moles = vol*conc #in moles

        mass = moles * mw #in grams, this is grams in 1L

        dict_of_mgml[enzyme] = mass

    return dict_of_mgml