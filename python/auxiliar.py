import cv2 as cv
import matplotlib
import numpy as np
import random

matplotlib.use('Agg')

from itertools import cycle
from matplotlib import colors as mcolors
from matplotlib import pyplot as plt
from pls_classifier import PLSClassifier
from sklearn.metrics import auc
from sklearn.metrics import average_precision_score
from sklearn.metrics import precision_recall_curve
from sklearn.metrics import roc_curve


def load_txt_file(file_name):
    this_file = open(file_name, 'r')
    this_list = []
    for line in this_file:
        line = line.rstrip()
        components = line.split()
        this_list.append(components)
    return this_list


def split_known_unknown_sets(complete_tuple_list, known_set_size=0.5):
    label_set = set()
    for (path, label) in complete_tuple_list:
        label_set.add(label)

    known_set = set(random.sample(label_set, int(known_set_size * len(label_set))))
    unknown_set = label_set - known_set
    
    known_tuple = [(path, label) for (path, label) in complete_tuple_list if label in known_set]
    unknown_tuple = [(path, label) for (path, label) in complete_tuple_list if label in unknown_set]
    
    return known_tuple, unknown_tuple


def split_train_test_samples(complete_tuple_list, train_set_samples=4):
    print('split_train_test_samples')
    to_shuffle = [item for item in complete_tuple_list]
    np.random.shuffle(to_shuffle)

    tuple_dict = dict()
    for (path, label) in to_shuffle:
        if tuple_dict.has_key(label):
            tuple_dict[label].append(path)
        else:
            tuple_dict[label] = [path]

    # for tuple in tuple_dict.iteritems():
    #     assert len(tuple[1]) > train_set_samples
    
    test_set = []
    train_set = []
    for (label, paths) in tuple_dict.iteritems():
        for path in paths[0:train_set_samples]:
            train_set.append((path, label))
        for path in paths[train_set_samples:len(paths)]: 
            test_set.append((path, label))

    return train_set, test_set


def split_train_test_sets(complete_tuple_list, train_set_size=0.5):
    from sklearn.model_selection import train_test_split
    labels = []
    paths = []
    
    random_state = np.random.RandomState(0)
    for (path, label) in complete_tuple_list:
        labels.append(label)
        paths.append(path)
    
    random_gen = np.random.RandomState(0)
    path_train, path_test, label_train, label_test = train_test_split(paths, labels, train_size=train_set_size, random_state=random_gen)

    train_set = zip(path_train, label_train)
    test_set = zip(path_test, label_test)

    return train_set, test_set


def load_images(path, image_list, display=False):
    for name in image_list:
        image = cv.imread(path + '/' + name, cv.IMREAD_COLOR)
        if display:
            cv.imshow('img', image)
            cv.waitKey(20)
    if display:
        cv.destroyAllWindows()


def augment_gallery_set(image_sample):
    image_samples = []
    image_samples.append(image_sample)
    image_samples.append(cv.flip(image_sample, 1)) # vertical-axis flip
    rows,cols,dep = image_sample.shape
    for angle in range(-5,6,10):
        rot_matrix = cv.getRotationMatrix2D((rows/2, cols/2), angle, 1.1)
        image_samples.append(cv.warpAffine(image_sample, rot_matrix,(cols, rows)))
    return image_samples


def sliding_window(image, window_size, step_size):
    for y in xrange(0, image.shape[0], step_size):
        for x in xrange(0, image.shape[1], step_size):
            yield (x, y, image[y:y + window_size[1], x:x + window_size[0]])


def generate_pos_neg_dict(labels):
    to_shuffle = [item for item in labels]
    np.random.shuffle(to_shuffle)
    neg_set = map(lambda neg: (neg, -1), to_shuffle[0:(len(labels) / 2)])
    pos_set = map(lambda pos: (pos, +1), to_shuffle[(len(labels) / 2):len(labels)])
    full_set = neg_set + pos_set
    full_dict = dict((key, val) for key, val in full_set)
    return full_dict

def split_into_chunks(full_list, num_chunks):
    split_list = []
    chunk_size = int(len(full_list) / num_chunks) + 1
    for index in range(0, len(full_list), chunk_size):
        split_list.append(full_list[index:index+chunk_size])
    return split_list


def getModel(input_shape, nclasses=2):
    import keras
    from keras.datasets import mnist
    from keras.layers import Dense, Dropout
    from keras.models import Sequential
    from keras.optimizers import RMSprop
    from keras import callbacks

    model = Sequential()
    model.add(Dense(64, activation='relu', input_shape=input_shape))
    model.add(Dropout(0.2))
    model.add(Dense(nclasses, activation='softmax'))
    #model.summary()
    model.compile(loss='categorical_crossentropy', optimizer='adadelta', metrics=['accuracy'])#RMSprop()

    return model


def learn_fcn_model(X, Y, split):
    import keras
    from keras.utils import np_utils
    from keras import callbacks

    boolean_label = [(split[key]+1)/2 for key in Y]
    y_train = np_utils.to_categorical(boolean_label, 2)
    
    model = getModel(input_shape=X[0].shape)
    model.fit(X, y_train, batch_size=40, nb_epoch=100, verbose=0)
    return (model, split)


def learn_plsh_model(matrix_x, matrix_y, split):
    classifier = PLSClassifier()
    boolean_label = [split[key] for key in matrix_y]
    model = classifier.fit(np.array(matrix_x), np.array(boolean_label))
    return (model, split)


def generate_probe_histogram(individuals, values, extra_name):
    plt.clf()
    plt.bar(range(len(individuals)), values)
    if sample_name == result[0][0]:
        plt.savefig('plots/' + extra_name + '_' + str(NUM_HASH) + '_' + str(counter) + '_' + sample_name + '_' + result[0][0])
    else:
        plt.savefig('plots/' + extra_name + '_' + str(NUM_HASH) + '_' + str(counter) + '_' + sample_name + '_' + result[0][0] + '_ERROR')


def generate_precision_recall(y_label_list, y_score_list):
    """
    A system with high recall but low precision returns many results, but most of its predicted labels are incorrect when compared to the training labels. 
    A system with high precision but low recall is just the opposite, returning very few results, but most of its predicted labels are correct when compared to the training labels. 
    An ideal system with high precision and high recall will return many results, with all results labeled correctly.
    """
    # Prepare input data
    label_list = []
    score_list = []
    for line in y_label_list:
        temp_list = [item[1] for item in line]
        label_list.append(temp_list)
    for line in y_score_list:
        temp_list = [item[1] for item in line]
        score_list.append(temp_list)
    label_array = np.array(label_list)
    score_array = np.array(score_list)

    # Compute micro-average ROC curve and ROC area
    pr = dict()
    pr['precision'], pr['recall'], pr['thresh'] = precision_recall_curve(label_array.ravel(), score_array.ravel())
    pr['avg_precision'] = average_precision_score(label_array, score_array, average="micro")
    return pr


def generate_roc_curve(y_label_list, y_score_list):
    """
    ROC curves typically feature true positive rate on the Y axis, and false positive rate on the X axis. 
    This means that the top left corner of the plot is the ideal point - a false positive rate of zero, and a true positive rate of one. 
    This is not very realistic, but it does mean that a larger area under the curve (AUC) is usually better.
    """
    # Prepare input data
    label_list = []
    score_list = []
    for line in y_label_list:
        temp_list = [item[1] for item in line]
        label_list.append(temp_list)
    for line in y_score_list:
        temp_list = [item[1] for item in line]
        score_list.append(temp_list)
    label_array = np.array(label_list)
    score_array = np.array(score_list)

    # Compute micro-average ROC curve and ROC area
    roc = dict()
    roc['fpr'], roc['tpr'], roc['thresh'] = roc_curve(label_array.ravel(), score_array.ravel())
    roc['auc']  = auc(roc['fpr'], roc['tpr'])
    return roc


def plot_cmc_curve(cmc_scores, extra_name):
    """
    The CMC shows how often the biometric subject template appears in the ranks (1, 5, 10, 100, etc.), based on the match rate.
    It is a method of showing measured accuracy performance of a biometric system operating in the closed-set identification task. 
    Templates are compared and ranked based on their similarity.
    """
    # Setup plot details
    color_dict = dict(mcolors.BASE_COLORS, **mcolors.CSS4_COLORS)
    color_names = [name for name, color in color_dict.items()]
    colors = cycle(color_names)
    lw = 2

    # Plot Cumulative Matching Characteristic curve
    plt.clf()
    counter = 1
    for score, color in zip(cmc_scores, colors):
        x_axis = range(len(score))
        y_axis = score
        area = auc(x_axis, y_axis)/len(score)
        rank1 = score[0]
        plt.plot(x_axis, y_axis, lw=lw, color=color, label='CMC curve %d (area = %0.2f, rank-1 = %0.2f)' % (counter, area, rank1))
        counter += 1

    plt.xlim([0, len(score)])
    plt.ylim([0.0, 1.05])
    plt.xlabel('Rank')
    plt.ylabel('Accuracy Rate')
    plt.title('Cumulative Matching Characteristic')
    plt.legend(loc="lower right")
    plt.grid()
    if extra_name == None:
        plt.show()
    else:
        plt.savefig('./plots/CMC_' + extra_name + '.pdf')
    plt.close()


def plot_precision_recall(prs, extra_name=None):
    # Setup plot details
    color_dict = dict(mcolors.BASE_COLORS, **mcolors.CSS4_COLORS)
    color_names = [name for name, color in color_dict.items()]
    colors = cycle(color_names)
    lw = 2

    # Plot Precision-Recall curve
    plt.clf()
    for index, color in zip(range(len(prs)), colors):
        pr = prs[index]
        plt.plot(pr['recall'], pr['precision'], lw=lw, color=color, label='PR curve %d (area = %0.2f)' % (index+1, pr['avg_precision']))
    plt.xlabel('Recall')
    plt.ylabel('Precision')
    plt.ylim([0.0, 1.05])
    plt.xlim([0.0, 1.0])
    plt.title('Precision-Recall Curve')
    plt.legend(loc="lower left")
    plt.grid()
    if extra_name == None:
        plt.show()
    else:
        plt.savefig('./plots/PR_' + extra_name + '.pdf')
    plt.close()


def plot_roc_curve(rocs, extra_name=None):
    # Setup plot details
    color_dict = dict(mcolors.BASE_COLORS, **mcolors.CSS4_COLORS)
    color_names = [name for name, color in color_dict.items()]
    colors = cycle(color_names)
    lw = 2

    # Plot Receiver Operating Characteristic curve
    plt.clf()
    for index, color in zip(range(len(rocs)), colors):
        roc = rocs[index]
        plt.plot(roc['fpr'], roc['tpr'], color=color, lw=lw, label='ROC curve %d (area = %0.2f)' % (index+1, roc['auc']))
    plt.plot([0, 1], [0, 1], color='navy', lw=lw, linestyle='--')
    plt.xlim([0.0, 1.0])
    plt.ylim([0.0, 1.05])
    plt.xlabel('False Positive Rate')
    plt.ylabel('True Positive Rate')
    plt.title('Receiver Operating Characteristic')
    plt.legend(loc="lower right")
    plt.grid()
    if extra_name == None:
        plt.show()
    else:
        plt.savefig('./plots/ROC_' + extra_name + '.pdf')
    plt.close()
