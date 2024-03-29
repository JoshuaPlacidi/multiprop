import torch
import json
import matplotlib.pyplot as plt
import numpy as np
from collections import defaultdict
import itertools


class Logger(object):
	def __init__(self, info=None):
		'''
		class for storing the results from training and evaluating graph models
		params:
			- info (optional): a dictionary containing initialise informatio about the model and experimental enviroment
		'''

		self.logs = defaultdict(list)
		self.logs['info'] = info

		# set colours for plots
		self.train_col = 'lightseagreen'
		self.valid_col = 'mediumslateblue'
		self.test_col = 'orangered'
		self.alt_col = 'crimson'

	def log(self, results_dict):
		'''
		log information from a results dict
		params:
			- results_dict: a dictionary with keys as the metric names and values as the value of that metric

		returns:
			None
		'''

		sample_sets = ['train', 'valid', 'test']

		for k, v in results_dict.items():

			if k in sample_sets: # if this is results from a data subset
				self.logs[k + '_loss'].append(results_dict[k]['loss'])
				self.logs[k + '_roc'].append(results_dict[k]['roc'])

			else: # if this is data from training enviorment, e.g. learning rate
				self.logs[k].append(v)
		

	def save(self, filepath):
		'''
		save a all logs to specificed filepath
		params:
			- filepath: path to save logs to, must end with .json

		return:
			- None
		'''
		assert filepath.endswith('.json')
		with open(filepath, 'w') as fp:
			json.dump(self.logs, fp)

	def run_slice(self, run, run_list):
		'''
		calculates the starting and ending indicies of a desired run
		params:
			- run: integer indicating which run we want the range for
			- run_list: an array of all the logged run lists

		returns:
			run_slice: slice object starting at the begining of a run and ending at is final step
		'''
		run_start = run_list.index(run)
		run_end = len(run_list) - run_list[::-1].index(run)
		run_slice = slice(run_start, run_end)
		return run_slice

	def plot_run(self, run=None, save_path=None):
		'''
		plot metrics from a specified run, if no run is specified then the best run (lowest valid loss) is plotted
		params:
			- run: run number to plot
			- save_path: path to save plot to

		returns:
			None
		'''
		runs = self.logs['run']
		
		# if no run is specifed then use the best run (lowest valid loss)	
		if not run:
			best_valid_loss_idx = np.argmax(self.logs['valid_loss'])
			run = runs[best_valid_loss_idx]

		# define the slice range of the desired run
		run_start = runs.index(run)
		run_end = len(runs) - runs[::-1].index(run)
		run_slice = slice(run_start, run_end)

		fig = plt.figure(figsize=(14, 6.5), dpi=80)
		
		# plot loss curves
		fig.add_subplot(121)
		tl = plt.plot(self.logs['train_loss'][run_slice], c=self.train_col, label='train')
		vl = plt.plot(self.logs['valid_loss'][run_slice], c=self.valid_col, label='valid')

		# configure loss plot
		plt.ylabel('Loss')
		plt.yscale('log')
		plt.title('Loss Curves and Learning Rate')

		# plot lr curves ontop of loss curves
		lr = plt.gca().twinx().plot(self.logs['lr'][run_slice], c=self.alt_col, label='LR')
		plt.yscale('log')
		plt.ylabel('Learning Rate')
		
		# create legend for loss and lr curves
		lns = tl + vl + lr
		labs = [l.get_label() for l in lns]
		plt.legend(lns, labs, loc=0)

		# plot roc curves
		fig.add_subplot(122)
		plt.plot(self.logs['train_roc'][run_slice], c=self.train_col, label='train')
		plt.plot(self.logs['valid_roc'][run_slice], c=self.valid_col, label='valid')

		# configure roc plot
		plt.xlabel('Epoch')
		plt.ylabel('Reciever Operator Curve')
		plt.title('ROC')
		plt.legend()
	
		# save figure
		fig.tight_layout()
		if save_path:
			plt.savefig(save_path, format='eps')
		plt.show()
			
	def plot_hyperparam_search(self, filepath):
		'''
		plot the results of a hyperparameter search
		params:
			- filepath: the location of the hyperparameter log files

		returns:
			None
		'''

		# load logs from file
		with open(filepath) as json_file:
			hyperparam_logs = json.load(json_file)
		
		params = defaultdict(list)
		score = []

		# for each log save its hyperparameter values and its corresponding validation loss
		for log in hyperparam_logs:
			
			for k, v in log['info'].items():
				params[k].append(v)

			params['lr'].append(log['lr'][0])
			score.append(max(log['valid_roc']))

		# plot each parameter and save
		for p in params.keys():
			plt.scatter(params[p], score)
			plt.title(p)
			plt.xlabel(p)
			plt.ylabel('valid roc')
			plt.ylim(0,1)
			plt.savefig(p + '.eps', format='eps')	
			plt.show()

	def print(self, round_to=None):
		'''
		print overview of results from logs

		params:
			- round_to: (optional) the number of decimals to round metric results to

		returns:
			None, prints output to terminal
		'''

		# calculate how many runs to print
		runs = self.logs['run']
		num_runs = max(runs)

		# store losses and roc scores
		train_losses, train_rocs = [], []
		valid_losses, valid_rocs = [], []

		for r in range(1, num_runs+1):
			# TODO: rewrite to use run_slice() function instead of custom implementation
			run_start = runs.index(r)
			run_end = len(runs) - runs[::-1].index(r)

			# find the best model: i.e. model with lowest valdiation loss
			best_idx = min(
				range(len(self.logs['valid_loss'][run_start:run_end])),
				key=self.logs['valid_loss'][run_start:run_end].__getitem__
			)

			# get the other metric values from the best model and store them
			train_losses.append(self.logs['train_loss'][run_start:run_end][best_idx])
			train_rocs.append(self.logs['train_roc'][run_start:run_end][best_idx])
			valid_losses.append(self.logs['valid_loss'][run_start:run_end][best_idx])
			valid_rocs.append(self.logs['valid_roc'][run_start:run_end][best_idx])

		# print means and standard deviations over best models from each run
		train_loss_mean, train_loss_std = np.mean(train_losses), np.std(train_losses)
		train_roc_mean, train_roc_std = np.mean(train_rocs), np.std(train_rocs)
		valid_loss_mean, valid_loss_std = np.mean(valid_losses), np.std(valid_losses)
		valid_roc_mean, valid_roc_std = np.mean(valid_rocs), np.std(valid_rocs)		

		# if round_to number suplied then round outputs to round_to many decimal places
		if round_to:
			train_loss_mean, train_loss_std = round(train_loss_mean, round_to), round(train_loss_std, round_to)
			train_roc_mean, train_roc_std = round(train_roc_mean, round_to), round(train_roc_std, round_to)
			valid_loss_mean, valid_loss_std = round(valid_loss_mean, round_to), round(valid_loss_std, round_to)
			valid_roc_mean, valid_roc_std = round(valid_roc_mean, round_to), round(valid_roc_std, round_to)

		# print the results
		print('Results from {0} runs'.format(num_runs))
		print('Train mean loss {0} \pm {1}'.format(train_loss_mean, train_loss_std))
		print('Train mean roc  {0} \pm {1}'.format(train_roc_mean, train_roc_std))
		print('Valid mean loss {0} \pm {1}'.format(valid_loss_mean, valid_loss_std))
		print('Valid mean roc  {0} \pm {1}'.format(valid_roc_mean, valid_roc_std))

	def load(self, filepath):
		'''
		load a log file
		params:
			- filepath: path of file to load from
		
		returns:
			- None
		'''
		with open(filepath) as fp:
			self.logs = json.load(fp)

	def mean_values(self, metric_list):
		'''
		calculate the mean values for each epoch from a metric list
		params:
			- metric list of the list of lists format [epochs[values]], a list of epochs and the corresponding metric values at those epochs

		returns:
			list of lists of format [mean[epoch]], the mean metric value for each epoch
		'''
		# pivot the metric list from runlist[epoch[value]] to epoch[runlist[value]] so that we can calculate the mean of the metrics values at each epoch across runs
		epoch_metric = list(map(list, itertools.zip_longest(*metric_list, fillvalue=None)))
		epoch_metric[2].append(None)

		# remove Nones
		for e in range(len(epoch_metric)):
			epoch_metric[e] = [l for l in epoch_metric[e] if l is not None]

		# calculate mean for each epoch value
		mean_epoch_metric = list(map(np.mean, epoch_metric))
		
		return mean_epoch_metric


	def plot_metric(self, metric='valid_loss', save_path=None):
		'''
		plot a singluar metric from over multiple runs with a mean line
		params:
			- metric: the name of the metric to plot
			- save_path: (optional) path to save plot to

		returns:
			None
		'''

		# get the number of runs
		runs = self.logs['run']
		num_runs = max(runs)
		
		# define figure size
		fig = plt.figure(figsize=(14, 6.5), dpi=80)

		metric_list = []

		for r in range(1, num_runs+1): # for each run

			# get the index of the start and end of the current run
			run_start = runs.index(r)
			run_end = len(runs) - runs[::-1].index(r)

			# get this runs metric values by indexes the metric list with the runs start and end indicies
			run_metric = self.logs[metric][run_start:run_end]
			metric_list.append(run_metric)

			# plot this runs metric values
			plt.plot(
				range(0, run_end - run_start), 
				run_metric,
				color="lightgrey"
			)

		mean_epoch_metric = self.mean_values(metric_list=metric_list)

		# plot the means
		plt.plot(range(0, max(self.logs['epoch'])), mean_epoch_metric, label='mean')
		plt.title(metric)
		plt.xlabel('Epoch')
		plt.ylabel(metric)
#		plt.yscale('log')
		plt.legend()

		# if save_path is specified then save figure
		if save_path:		
			assert save_path.endswith('eps')
			plt.savefig(save_path, format='eps')
		
		plt.show()

		
	def plot_experiment_metric_curves(self, filepath, metric='valid_loss'):
		'''
		plot the results from each model from an experiment on the same graph
		params:
			- filepath: path of the experiment logs
			- metric: the metric to plot

		returns:
			None
		'''

		# load experiment logs from file
		with open(filepath) as json_file:
			experiment_logs = json.load(json_file)


		for log in experiment_logs:

			metric_list = []
			for run in range(1, log['info']['num_runs']+1):
				# define the slice range of the desired run
				run_slice = self.run_slice(run, log['run'])
				metric_list.append(log[metric][run_slice])

			mean_epoch_metric = self.mean_values(metric_list=metric_list)

			plt.plot(range(0, len(mean_epoch_metric)), mean_epoch_metric, label=log['info']['model_type'])

		plt.xlabel('Epoch')
		plt.ylabel(metric)
		plt.legend()
		plt.show()
		

	def plot_experiment_comparison(self, filepath, metric='valid_loss', comparitor='trainable_parameters'):
		'''
		plot a scatter plot comparing two metrics, for example the validation loss against the number of trainable parameters
		params:
			- metric: the metric to plot
			- comparitor: the metric to plot again

		returns:
			None
		'''

		# load experiment logs from file
		with open(filepath) as json_file:
			experiment_logs = json.load(json_file)

		# if a big value is better or worse for this metric
		if metric.endswith('loss'):
			operator = min
		else:
			operator = max

		for log in experiment_logs:

			metric_values = []
			for run in range(1, log['info']['num_runs']+1):
				# define the slice range of the desired run
				run_slice = self.run_slice(run, log['run'])
				best_value = operator(log[metric][run_slice])
				metric_values.append(best_value)

			plt.plot(log['info'][comparitor], np.mean(metric_values), label = log['info']['model_type'], marker='o')
			print('Model {0} {1}: {2}'.format(log['info']['model_type'], metric, best_value))

		plt.legend()
		plt.show()

	
	def print_experiment(self, filepath):
		'''
		print the output from an experiment
		params:
			- filepath: the path of the experimental logs

		returns:
			None
		'''
		
		with open(filepath) as json_file:
			experiment_logs = json.load(json_file)

		for log in experiment_logs:
			print(log['info']['model_type'])
			self.logs = log
			self.print(round_to=3)
			print('\n')
