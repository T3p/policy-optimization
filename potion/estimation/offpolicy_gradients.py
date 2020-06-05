#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Policy gradient stimators
@author: Matteo Papini
"""

import torch
import potion.common.torch_utils as tu
from potion.common.misc_utils import unpack, discount
from potion.common.torch_utils import tensormat, jacobian
from potion.estimation.moments import incr_mean, incr_var


def off_gpomdp_estimator(batch, disc, policy, target_params, 
                         baselinekind='avg', 
                         result='mean',
                         shallow=False):
    """G(PO)MDP policy gradient estimator
       
    batch: list of N trajectories generated by behavioral policy. Each trajectory is a tuple 
        (states, actions, rewards, mask). Each element of the tuple is a 
        tensor where the first dimension is time.
    disc: discount factor
    policy: the one used to collect the data
    target_params: parameters of the policy to evaluate
    baselinekind: kind of baseline to employ in the estimator. 
        Either 'avg' (average reward, default), 'peters' 
        (variance-minimizing),  or 'zero' (no baseline)
    result: whether to return the final estimate ('mean', default), or the 
        single per-trajectory estimates ('samples')
    shallow: whether to use precomputed score functions (only available
        for shallow policies)
    """
    if shallow:
        return _shallow_off_gpomdp_estimator(batch, disc, policy, target_params, baselinekind, result)
    else:
        raise NotImplementedError

"From Mastrangelo's master thesis"
def _shallow_off_gpomdp_estimator(batch, disc, policy, target_params, 
                                  baselinekind='peters', 
                                  result='mean'):
    with torch.no_grad():        
        states, actions, rewards, mask, _ = unpack(batch) # NxHxm, NxHxd, NxH, NxH
        
        disc_rewards = discount(rewards, disc) #NxH
        scores = policy.score(states, actions) #NxHxM
        G = torch.cumsum(tensormat(scores, mask), 1) #NxHxm
        n_k = torch.sum(mask, dim=0) #H
        n_k[n_k==0.] = 1.
        behavioral_logps = policy.log_pdf(states, actions) #NxH
        behavioral_params = policy.get_flat()
        policy.set_from_flat(target_params)
        target_logps = policy.log_pdf(states, actions) #NxH
        policy.set_from_flat(behavioral_params)
        log_iws = torch.cumsum(target_logps - behavioral_logps, 1) #NxH
        stabilizers, _ = torch.max(log_iws, dim=1, keepdim=True) #NxH
        
        if baselinekind == 'peters':
            baseline = torch.sum(tensormat(G ** 2, disc_rewards * torch.exp(2*(log_iws - stabilizers))), 0) / \
                            torch.sum(tensormat(G ** 2, torch.exp(2*(log_iws - stabilizers))), 0) #Hxm
        elif baselinekind == 'zero':
            baseline = torch.zeros_like(G[0]) #Hxm
        else:
            raise NotImplementedError
        baseline[baseline != baseline] = 0 #removes non-real values
        values = disc_rewards.unsqueeze(2) - baseline.unsqueeze(0) #NxHxm
        
        _samples = torch.sum(tensormat(G * values, mask * torch.exp(log_iws)), 1) #Nxm
        if result == 'samples':
            return _samples #Nxm
        else:
            return torch.mean(_samples, 0) #m
    

#entropy-augmented version
def egpomdp_estimator(batch, disc, policy, coeff, baselinekind='avg', result='mean',
                     shallow=False):
    """G(PO)MDP policy gradient estimator
       
    batch: list of N trajectories. Each trajectory is a tuple 
        (states, actions, rewards, mask). Each element of the tuple is a 
        tensor where the first dimension is time.
    disc: discount factor
    policy: the one used to collect the data
    coeff: entropy bonus coefficient
    baselinekind: kind of baseline to employ in the estimator. 
        Either 'avg' (average reward, default), 'peters' 
        (variance-minimizing),  or 'zero' (no baseline)
    result: whether to return the final estimate ('mean', default), or the 
        single per-trajectory estimates ('samples')
    shallow: whether to use precomputed score functions (only available
        for shallow policies)
    """
    if shallow:
        return _shallow_egpomdp_estimator(batch, disc, policy, coeff, baselinekind, result)    
    else:
        raise NotImplementedError


def reinforce_estimator(batch, disc, policy, baselinekind='avg', 
                        result='mean', shallow=False):
    """REINFORCE policy gradient estimator
       
    batch: list of N trajectories. Each trajectory is a tuple 
        (states, actions, rewards, mask). Each element of the tuple is a 
        tensor where the first dimension is time.
    disc: discount factor
    policy: the one used to collect the data
    baselinekind: kind of baseline to employ in the estimator. 
        Either 'avg' (average reward, default), 'peters' 
        (variance-minimizing),  or 'zero' (no baseline)
    result: whether to return the final estimate ('mean', default), or the 
        single per-trajectory estimates ('samples')
    shallow: whether to use precomputed score functions (only available
        for shallow policies)
    """
    raise NotImplementedError


#entopy-augmented version     
def _shallow_egpomdp_estimator(batch, disc, policy, coeff, baselinekind='peters', result='mean'):
    raise NotImplementedError

        
def _shallow_reinforce_estimator(batch, disc, policy, baselinekind='peters', result='mean'):
    raise NotImplementedError


def _incr_shallow_gpomdp_estimator(traj, disc, policy, baselinekind='peters', result='mean', cum_1 = 0., cum_2 = 0., cum_3 = 0., tot_trajs = 1):
    raise NotImplementedError

        
"""Testing"""
if __name__ == '__main__':
    from potion.actors.continuous_policies import ShallowGaussianPolicy as Gauss
    from potion.simulation.trajectory_generators import generate_batch
    from potion.common.misc_utils import seed_all_agent
    import potion.envs
    import gym.spaces
    from potion.estimation.gradients import gpomdp_estimator
    
    env = gym.make('ContCartPole-v0')
    env.seed(0)
    seed_all_agent(0)
    N = 100
    H = 100
    disc = 0.99
    pol = Gauss(4,1, mu_init=[0.,0.,0.,0.], learn_std=True)
    
    batch = generate_batch(env, pol, H, N)
    
    on = gpomdp_estimator(batch, disc, pol, baselinekind='peters', 
                         shallow=True)
    
    off = off_gpomdp_estimator(batch, disc, pol, pol.get_flat(), 
                               baselinekind='peters',
                               shallow=True)
    print(on, off)
    