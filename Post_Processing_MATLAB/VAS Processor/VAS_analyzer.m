%% 2024-25 Vickrey VAS Study - Determining Value Landscape
% This code determines a participant's Value Landscape when using the Dephy 
% Ankle Exoskeletons and a Research Prototype Knee Exoskeleton.
%
% Script should be run from the Exoboot-Controller-VAS/Post_Processing_MATLAB/VAS Processor directory
% Author: Nundini Rawal
% Date: 9/21/2024

clc; close; clear;

% ask for path to Vickrey subject file tree
fprintf("Select Location of the VAS File Tree\n");
title = 'Select Location of the VAS File Tree (i.e. all VAS subject folders should be viewable';
path = '/Volumes/me-neurobionics/Lab Members/Students/Nundini Rawal/SUBJECT DATA/Vickrey_Data_Analysis/VAS_Protocol_Data/';
VAS_directory_path = uigetdir(path,title);

% ask for path to subject dictionary file tree
fprintf("Select Location of the subject dictionary file\n");
sub_dict_path = '/Volumes/me-neurobionics/Lab Members/Students/Nundini Rawal/SUBJECT DATA/Vickrey_Data_Analysis/';
[~,sub_dictionary_file_location] = uigetfile(sub_dict_path);

% ask for path to figure folder (to save generated figures to)
fprintf("Select Folder Where you'd like to Save Generated Figures\n");
fig_gen_path = '/Volumes/me-neurobionics/Lab Members/Students/Nundini Rawal/SUBJECT DATA/Vickrey_Data_Analysis/VAS_Protocol_Data/';
figure_path = uigetdir(path);

% add VAS directory & subject dictionary to path
addpath(genpath(VAS_directory_path))
addpath(genpath(sub_dictionary_file_location))
addpath(genpath(figure_path))

% loading in subject info from dictionary
[subject, subject_list] = subject_dictionary_VAS;

% specify subj numbers (remove subjects due to any criteria)
subj_num = [1 2];

%% Plot Each Trial and Averaged Trajectory for Selected Subjects

for sub_num = subj_num

    % load file
    xls_sheet = subject(sub_num).VAS_filename_4BTN;
    exp_data_sheet = readmatrix(xls_sheet);
    
    % extract data
    rows_2_extract = 1:size(exp_data_sheet(1:end,1));
    % if sub_num == 2
    %     rows_2_extract = 1:9;
    % elseif sub_num == 3
    %     rows_2_extract = 1:size(exp_data_sheet(1:end,1));
    % end
    
    btn_num = exp_data_sheet(rows_2_extract,1);
    trial_num = exp_data_sheet(rows_2_extract,2);
    pres_num = exp_data_sheet(rows_2_extract,3);
    torques = exp_data_sheet(rows_2_extract,4:2:10);   
    values = exp_data_sheet(rows_2_extract,[5 7 9 11]);
    max_trial_num = max(trial_num);
    max_pres_num = max(pres_num);
    total_options = max_pres_num*btn_num(1);

    % compile into columns for each trial
    reshaped_torques = reshape(torques', total_options, max_trial_num);
    reshaped_values = reshape(values', total_options, max_trial_num);

    % normalize data
    normd_torques = reshaped_torques/max(reshaped_torques,[],"all");
   
    % sort torque cols into ascending order & apply sort filter to values
    [sorted_torques,sort_idxs] = sort(normd_torques);
    sorted_values = reshaped_values(sort_idxs,:);

    % find average $-values
    avg_vals = mean(sorted_values(1:total_options,:),2);
    std_vals = std(sorted_values(1:total_options,:),0,2);

    % Fit best-fit curve
    x = sorted_torques(:,1);
    curve_fit = fit(x,avg_vals,'poly4','normalize','on');

    % Compute shading bounds
    upper_bound = avg_vals + std_vals;
    lower_bound = avg_vals - std_vals;

    % plot data
    figure()
    colors = {"#0072BD", "#D95319", "#EDB120", "#A2142F", "#7E2F8E", "#4DBEEE"};
    for trial = 1:max_trial_num
        plot(sorted_torques(1:total_options,trial),sorted_values(1:total_options,trial),'.','MarkerSize',20, 'color',colors{trial});
        hold on
    end

    % Add shaded region
    fill([x; flipud(x)], [upper_bound; flipud(lower_bound)], 'k', 'FaceAlpha', 0.2, 'EdgeColor', 'none');
    
    % plot avg points & trajectory
    cfit = plot(curve_fit);
    set(cfit,'color','k','LineWidth',2)
    errorbar(sorted_torques(:,1),avg_vals,std_vals,'.k','MarkerSize', 20);

    if (sub_num == 1) || (sub_num == 2)
        legend({'trial 1';'trial 2';'trial 3';'trial 4'; 'curve fit'; 'trial averages with std'});
    else
        legend({'trial 1';'trial 2';'trial 3';'trial 4';'trial 5'; 'trial 6'; 'curve fit'; 'trial averages with std'});
    end
    
    xlabel("Normalized Torque")
    ylabel("$/Hour")

    % save the current figure if it doesn't exist
    VAS_fig_name = string(figure_path)+"/S10"+string(sub_num)+'_VAS_4BTN.svg';
        
    if exist(VAS_fig_name,'file') == 0
        saveas(gcf,VAS_fig_name);
    end
    
end

%% Plot 10-button Trajectories for Selected Subjects

% specify subj numbers (remove subjects due to any criteria)
subj_num = [2 3];

for sub_num = subj_num

    % load file
    xls_sheet = subject(sub_num).VASfilename;
    exp_data_sheet = readmatrix(xls_sheet);
    
    % extract data
    if sub_num == 2
        rows_2_extract = 10:11;
    elseif sub_num == 3
        rows_2_extract = 1:size(exp_data_sheet(1:end,1));
    end
    
    % extract data
    btn_num = exp_data_sheet(rows_2_extract,1);
    trial_num = exp_data_sheet(rows_2_extract,2);
    pres_num = exp_data_sheet(rows_2_extract,3);
    torques = exp_data_sheet(rows_2_extract,4:2:26);
    values = exp_data_sheet(rows_2_extract,5:2:27);
    max_trial_num = max(trial_num);
    max_pres_num = max(pres_num);
    total_options = max_pres_num*btn_num(1);

    % compile into columns for each trial
    reshaped_torques = reshape(torques', total_options, max_trial_num);
    reshaped_values = reshape(values', total_options, max_trial_num);

    % normalize data
    normd_torques = reshaped_torques/max(reshaped_torques,[],"all");
   
    % sort torque cols into ascending order & apply sort filter to values
    [sorted_torques,sort_idxs] = sort(normd_torques);
    sorted_values = reshaped_values(sort_idxs,:);

    % find average $-values
    avg_vals = mean(sorted_values(1:total_options,:),2);
    std_vals = std(sorted_values(1:total_options,:),0,2);

    % Fit best-fit curve
    x = sorted_torques(:,1);
    curve_fit = fit(x,avg_vals,'poly4','normalize','on');

    % plot data
    figure()
    colors = {'b', 'r', 'g'};
    for trial = 1:max_trial_num
        plot(sorted_torques(1:total_options,trial),sorted_values(1:total_options,trial),'.','MarkerSize',20, 'color',colors{trial});
        hold on
    end
    
    % plot avg points & trajectory
    cfit = plot(curve_fit);
    set(cfit,'color','k','LineWidth',2)
    errorbar(sorted_torques(:,1),avg_vals,std_vals,'.k','MarkerSize', 20);

    if sub_num == 2
        legend({'trial 1';'trial 2';'curve fit'; 'trial averages with std'});
    elseif sub_num == 3
        legend({'trial 1';'curve fit'; 'trial averages with std'});
    end
    xlabel("Normalized Torque")
    ylabel("$/Hour")
    
end

   






