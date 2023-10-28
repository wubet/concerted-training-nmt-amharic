import os

import matplotlib.pyplot as plt


def plot_graph(epoch_data, args):
    # Ensure the output directory exists
    output_dir = "output"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Extract data for plotting
    epochs = [data[0] for data in epoch_data]
    losses = [data[1] for data in epoch_data]
    accuracies = [data[2] for data in epoch_data]
    learning_rates = [data[3] for data in epoch_data]  # Extract learning rates

    # Language mapping based on args
    language_map = {"en": "English", "am": "Amharic"}
    source_language = language_map.get(args.s, args.s)
    target_language = language_map.get(args.t, args.t)

    # Generate plot labels based on source and target languages
    loss_label = f"{source_language} to {target_language} CTNMT Training Loss"
    accuracy_label = f"{source_language} to {target_language} CTNMT Training Accuracy"
    lr_label = f"{source_language} to {target_language} CTNMT Learning Rate Schedule"

    # Plot loss against epochs
    plt.figure(figsize=(6, 5))
    plt.plot(epochs, losses, '-o', label='loss')
    plt.title(f'{loss_label}')
    plt.xlabel('Epochs')
    plt.ylabel('Loss')
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "training_loss.png"))  # Save the loss plot
    plt.close()  # Close the current plot

    # Plot accuracy against epochs
    plt.figure(figsize=(6, 5))
    plt.plot(epochs, accuracies, '-o', label='accuracy')
    plt.title(f'{accuracy_label}')
    plt.xlabel('Epochs')
    plt.ylabel('Accuracy')
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "training_accuracy.png"))  # Save the accuracy plot
    plt.close()  # Close the current plot

    # Plot learning rate against epochs
    plt.figure(figsize=(6, 5))
    plt.plot(epochs, learning_rates, '-o', label='learning rate', color='green')
    plt.title(f'{lr_label}')
    plt.xlabel('Epochs')
    plt.ylabel('Learning Rate')
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "learning_rate.png"))  # Save the learning rate plot
    plt.close()  # Close the current plot
